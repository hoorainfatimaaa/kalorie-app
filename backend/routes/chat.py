from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.meal import Meal,UserMealContext
from database.db import db
import traceback
from models.chat_message import ChatMessage
import os
import uuid
from werkzeug.utils import secure_filename
from models.user import User
from models.diet_plan import DietPlan
from models.temp_diet_plan import TempDietPlan
from services.openai_service import ask_openai, transcribe,generate_audio
from services.nutrition_service import calculate_calorie_goal, calculate_macro_goals
from sqlalchemy import func
from datetime import date
import json
chat = Blueprint("chat", __name__)
def clean_text(value):
    if isinstance(value, str):
        return value.replace("\x00", "")
    return value
today = date.today()

DISPLAY_INTENTS = {
    "show_profile",
    "show_progress",
    "calorie_status",
    "show_meal_history",
    "show_weekly_plan",
}


def user_has_complete_profile(user):
    """calculate_bmr/calculate_tdee need these fields; bail out safely if any are missing."""
    return all([
        user is not None,
        user.age is not None,
        user.height is not None,
        user.weight is not None,
        user.gender is not None,
        user.fitness_goal is not None,
    ])


def get_today_totals(user_id):
    """Sum calories/protein/carbs/fat for this user's meals logged today."""
    result = db.session.query(
        func.coalesce(func.sum(Meal.calories), 0),
        func.coalesce(func.sum(Meal.protein), 0),
        func.coalesce(func.sum(Meal.carbs), 0),
        func.coalesce(func.sum(Meal.fat), 0),
    ).filter(
        Meal.user_id == user_id,
        func.date(Meal.created_at) == date.today()
    ).first()

    return {
        "calories": result[0] or 0,
        "protein": result[1] or 0,
        "carbs": result[2] or 0,
        "fat": result[3] or 0,
    }


def build_profile_data(user):
    return {
        "full_name": user.full_name,
        "email": user.email,
        "age": user.age,
        "gender": user.gender,
        "height": user.height,
        "weight": user.weight,
        "activity_level": user.activity_level,
        "fitness_goal": user.fitness_goal,
        "dietary_preferences": user.dietary_preferences,
        "allergies": user.allergies,
    }


def build_progress_data(user, user_id):
    calorie_goal = calculate_calorie_goal(user)
    macros = calculate_macro_goals(user)
    consumed = get_today_totals(user_id)

    return {
        "calorie_goal": calorie_goal,
        "calories_consumed": consumed["calories"],
        "calories_remaining": max(calorie_goal - consumed["calories"], 0),
        "protein_goal": macros["protein_goal"],
        "protein_consumed": consumed["protein"],
        "protein_remaining": max(macros["protein_goal"] - consumed["protein"], 0),
        "carbs_goal": macros["carbs_goal"],
        "carbs_consumed": consumed["carbs"],
        "carbs_remaining": max(macros["carbs_goal"] - consumed["carbs"], 0),
        "fat_goal": macros["fat_goal"],
        "fat_consumed": consumed["fat"],
        "fat_remaining": max(macros["fat_goal"] - consumed["fat"], 0),
    }


def build_calorie_status_data(user, user_id):
    calorie_goal = calculate_calorie_goal(user)
    consumed = get_today_totals(user_id)["calories"]

    if consumed > calorie_goal:
        exceeded = True
        exceeded_by = consumed - calorie_goal
        calories_remaining = 0
    else:
        exceeded = False
        exceeded_by = 0
        calories_remaining = calorie_goal - consumed

    return {
        "calorie_goal": calorie_goal,
        "calories_consumed": consumed,
        "calories_remaining": calories_remaining,
        "exceeded": exceeded,
        "exceeded_by": exceeded_by,
    }


def build_meal_history_data(user_id, limit=20):
    """Most recent logged meals for this user, from the database (not chat history)."""
    meals = (
        Meal.query
        .filter_by(user_id=user_id)
        .order_by(Meal.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "meals": [
            {
                "id": m.id,
                "meal_name": m.meal_name,
                "portion": m.portion,
                "calories": m.calories,
                "protein": m.protein,
                "carbs": m.carbs,
                "fat": m.fat,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in meals
        ]
    }


def apply_display_intent(ai_reply, user, user_id, current_plan):
    """
    If ai_reply's intent is one of the new read-only display intents,
    attach backend-sourced `data` to it (and override `reply` for the
    no-data edge cases). Mutates and returns ai_reply. No-op otherwise.
    """
    if not isinstance(ai_reply, dict):
        return ai_reply

    intent = ai_reply.get("intent")
    if intent not in DISPLAY_INTENTS:
        return ai_reply

    if intent == "show_profile":
        ai_reply["data"] = build_profile_data(user)

    elif intent == "show_progress":
        if not user_has_complete_profile(user):
            ai_reply["reply"] = (
                "Please complete your profile (age, height, weight, gender, "
                "and fitness goal) so I can calculate your progress."
            )
            ai_reply["data"] = None
        else:
            ai_reply["data"] = build_progress_data(user, user_id)

    elif intent == "calorie_status":
        if not user_has_complete_profile(user):
            ai_reply["reply"] = (
                "Please complete your profile (age, height, weight, gender, "
                "and fitness goal) so I can calculate your calorie status."
            )
            ai_reply["data"] = None
        else:
            ai_reply["data"] = build_calorie_status_data(user, user_id)

    elif intent == "show_meal_history":
        ai_reply["data"] = build_meal_history_data(user_id)

    elif intent == "show_weekly_plan":
        ai_reply["data"] = {"plan": current_plan}
        if not current_plan:
            ai_reply["reply"] = "You don't have a saved weekly meal plan yet."

    return ai_reply


@chat.route("/chat", methods=["POST"])
@jwt_required()
def chat_with_ai():

    try:

        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        meals = Meal.query.filter(Meal.user_id == user_id,func.date(Meal.created_at) == today).order_by(Meal.created_at.desc()).all()
        
        chat_history = ChatMessage.query.filter_by(user_id=user_id).order_by(ChatMessage.created_at.asc()).all()
        message = request.form.get("message", "").strip()
        image = request.files.get("image")
        image_path = None

        if image:

            filename = secure_filename(image.filename)

            extension = os.path.splitext(filename)[1]#split filename and file type and takes file type

            unique_filename = f"{uuid.uuid4()}{extension}"

            upload_folder = os.path.join(os.getcwd(), "uploads")#gets current folder and creates folder 

            os.makedirs(upload_folder, exist_ok=True)#if nothin exists or else upload

            full_path = os.path.join(upload_folder, unique_filename)

            image.save(full_path)

            image_path = unique_filename

        if message or image:

            user_message = ChatMessage(
                user_id=user_id,
                sender="user",
                message=message if message else "",
                image_path=image_path,
                message_type="image" if image else "text"
                )

            db.session.add(user_message)
            db.session.commit()
        current_plan = None
    
        temp_plan = TempDietPlan.query.filter_by(user_id=user_id).order_by(TempDietPlan.created_at.desc()).first()

        if temp_plan:
           current_plan = temp_plan.plan_data

        else:
            saved_plan = DietPlan.query.filter_by(user_id=user_id).order_by(DietPlan.id.asc()).all()


            if saved_plan:

                current_plan = []

                days = {}

                for meal in saved_plan:

                   if meal.day not in days:
                       days[meal.day] = {"day": meal.day,"meals": []}


                   days[meal.day]["meals"].append({

                "meal_type": meal.meal_type,
                "meal_name": meal.meal_name,
                "description": meal.description,
                "calories": meal.calories,
                "protein": meal.protein,
                "carbs": meal.carbs,
                "fat": meal.fat

            })

                current_plan = list(days.values())
        

        ai_reply = ask_openai(
        message=message,
        image=image,
        user=user,
        meals=meals,
        chat_history=chat_history,
        current_plan=current_plan
)  
        ai_reply = apply_display_intent(ai_reply, user, user_id, current_plan)

        ai_message = ChatMessage(
        user_id=user_id,
        sender="ai",
        message=json.dumps(ai_reply)
)

        db.session.add(ai_message)
        db.session.commit()
        
        if isinstance(ai_reply, dict) and ai_reply.get("intent") == "meal_log":

            meal = Meal(
                user_id=user_id,
                meal_name=ai_reply.get("meal_name"),
                calories=ai_reply.get("calories"),
                protein=ai_reply.get("protein"),
                carbs=ai_reply.get("carbs"),
                fat=ai_reply.get("fat"),
                portion=ai_reply.get("portion"),
                is_estimated=ai_reply.get("is_estimated", True))

            db.session.add(meal)
            db.session.commit()
            context = UserMealContext.query.filter_by(user_id=user_id).first()
            if context:

                context.last_meal_id = meal.id
            else:

                context = UserMealContext(
                user_id=user_id,
                last_meal_id=meal.id
            )

                db.session.add(context)


            db.session.commit()

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "meal_update":


            context = UserMealContext.query.filter_by(
                user_id=user_id
            ).first()


            if context:

                meal = Meal.query.get(
                context.last_meal_id
                )


                if meal:

                    if ai_reply.get("meal_name"):
                        meal.meal_name = ai_reply.get("meal_name")

                    if ai_reply.get("calories") is not None:
                        meal.calories = ai_reply.get("calories")

                    if ai_reply.get("protein") is not None:
                        meal.protein = ai_reply.get("protein")

                    if ai_reply.get("carbs") is not None:
                        meal.carbs = ai_reply.get("carbs")

                    if ai_reply.get("fat") is not None:
                        meal.fat = ai_reply.get("fat")

                    if ai_reply.get("portion"):
                        meal.portion = ai_reply.get("portion")

                    if ai_reply.get("is_estimated") is not None:
                        meal.is_estimated = ai_reply.get("is_estimated")


                    db.session.commit()
        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "meal_delete":

            context = UserMealContext.query.filter_by(
                user_id=user_id
            ).first()

            if context and context.last_meal_id:

                meal = Meal.query.get(
                    context.last_meal_id
                )

                if meal:

                    db.session.delete(meal)

                db.session.delete(context)
                db.session.commit()
        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "save_diet_plan":


            temp_plan = TempDietPlan.query.filter_by(
                user_id=user_id
            ).order_by(
                TempDietPlan.created_at.desc()
            ).first()
            
            if temp_plan:

                DietPlan.query.filter_by(
                    user_id=user_id
                ).delete()


                for day in temp_plan.plan_data:

                    for meal in day.get("meals", []):


                        diet_meal = DietPlan(

                            user_id=user_id,

                            day=day.get("day"),

                            meal_type=clean_text(meal.get("meal_type")),

                            meal_name=clean_text(meal.get("meal_name")),

                            description=clean_text(meal.get("description")),

                            calories=meal.get("calories"),

                            protein=meal.get("protein"),

                            carbs=meal.get("carbs"),

                            fat=meal.get("fat"))

                        db.session.add(diet_meal)


                db.session.delete(temp_plan)


                db.session.commit()         
        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "diet_plan_confirmation":

            plan = ai_reply.get("plan")


            if plan:


                TempDietPlan.query.filter_by(
                    user_id=user_id
                ).delete()

                temp = TempDietPlan(
                    user_id=user_id,
                    plan_data=plan
                )

                db.session.add(temp)
                db.session.commit()

        return jsonify({
                "success": True,
                "user_id": user_id,
                "reply": ai_reply
            }), 200

    except Exception as e:
        traceback.print_exc()

        return jsonify({
        "success": False,
        "message": str(e)
    }), 500
@chat.route("/chat/audio", methods=["POST"])
@jwt_required()
def chat_audio():

    try:

        user_id = get_jwt_identity()

        user = User.query.get(user_id)


        meals = Meal.query.filter_by(
            user_id=user_id
        ).order_by(
            Meal.created_at.desc()
        ).all()


        chat_history = ChatMessage.query.filter_by(
            user_id=user_id
        ).order_by(
            ChatMessage.created_at.asc()
        ).all()

        audio = request.files.get("audio")
        if not audio:

            return jsonify({
                "success": False,
                "message": "No audio received."
            }), 400



        filename = secure_filename(audio.filename)

        extension = os.path.splitext(filename)[1]

        unique_filename = f"{uuid.uuid4()}{extension}"
        upload_folder = os.path.join(
            os.getcwd(),
            "uploads"
        )

        os.makedirs(
            upload_folder,
            exist_ok=True
        )
        full_path = os.path.join(
            upload_folder,
            unique_filename
        )


        audio.save(full_path)

        transcript = transcribe(full_path)
        print("Transcript:", transcript)



        user_message = ChatMessage(
            user_id=user_id,
            sender="user",
            message=transcript,
            message_type="audio",
            audio_path=unique_filename
        )


        db.session.add(user_message)

        db.session.commit()

        current_plan = None


        temp_plan = TempDietPlan.query.filter_by(
            user_id=user_id
        ).order_by(
            TempDietPlan.created_at.desc()
        ).first()



        if temp_plan:

            current_plan = temp_plan.plan_data

        else:

            saved_plan = DietPlan.query.filter_by(
                user_id=user_id
            ).all()



            if saved_plan:

                days = {}
                for meal in saved_plan:


                    if meal.day not in days:

                        days[meal.day] = {
                            "day": meal.day,
                            "meals": []
                        }
                    days[meal.day]["meals"].append({

                        "meal_type": meal.meal_type,

                        "meal_name": meal.meal_name,

                        "description": meal.description,

                        "calories": meal.calories,

                        "protein": meal.protein,

                        "carbs": meal.carbs,

                        "fat": meal.fat

                    })

                current_plan = list(days.values())

        ai_reply = ask_openai(
            message=transcript,
            image=None,
            user=user,
            meals=meals,
            chat_history=chat_history,
            current_plan=current_plan
        )

        ai_reply = apply_display_intent(ai_reply, user, user_id, current_plan)

        ai_message = ChatMessage(
    user_id=user_id,
    sender="ai",
    message=json.dumps(ai_reply),
    message_type="text"
)


        db.session.add(ai_message)

        db.session.commit()

        if isinstance(ai_reply, dict) and ai_reply.get("intent") == "meal_log":


            meal = Meal(

                user_id=user_id,

                meal_name=ai_reply.get("meal_name"),

                calories=ai_reply.get("calories"),

                protein=ai_reply.get("protein"),

                carbs=ai_reply.get("carbs"),

                fat=ai_reply.get("fat"),

                portion=ai_reply.get("portion"),

                is_estimated=ai_reply.get("is_estimated", True)

            )


            db.session.add(meal)

            db.session.commit()



            context = UserMealContext.query.filter_by(
                user_id=user_id
            ).first()



            if context:

                context.last_meal_id = meal.id


            else:

                context = UserMealContext(
                    user_id=user_id,
                    last_meal_id=meal.id
                )

                db.session.add(context)
            db.session.commit()

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "meal_update":


            context = UserMealContext.query.filter_by(
                user_id=user_id
            ).first()

            if context:


                meal = Meal.query.get(
                    context.last_meal_id
                )


                if meal:


                    if ai_reply.get("meal_name"):

                        meal.meal_name = ai_reply.get("meal_name")


                    if ai_reply.get("calories") is not None:

                        meal.calories = ai_reply.get("calories")


                    if ai_reply.get("protein") is not None:

                        meal.protein = ai_reply.get("protein")


                    if ai_reply.get("carbs") is not None:

                        meal.carbs = ai_reply.get("carbs")


                    if ai_reply.get("fat") is not None:

                        meal.fat = ai_reply.get("fat")


                    if ai_reply.get("portion"):

                        meal.portion = ai_reply.get("portion")


                    if ai_reply.get("is_estimated") is not None:

                        meal.is_estimated = ai_reply.get("is_estimated")
                    db.session.commit()

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "meal_delete":


            context = UserMealContext.query.filter_by(
                user_id=user_id
            ).first()

            if context and context.last_meal_id:
                meal = Meal.query.get(
                    context.last_meal_id
                )

                if meal:

                    db.session.delete(meal)
                db.session.delete(context)

                db.session.commit()

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "save_diet_plan":


            temp_plan = TempDietPlan.query.filter_by(user_id=user_id).order_by(TempDietPlan.created_at.desc()).first()

            if temp_plan:


                DietPlan.query.filter_by(
                    user_id=user_id
                ).delete()

                for day in temp_plan.plan_data:
                    for meal in day.get("meals", []):
                        diet_meal = DietPlan(

                            user_id=user_id,

                            day=day.get("day"),

                            meal_type=meal.get("meal_type"),

                            meal_name=meal.get("meal_name"),

                            description=meal.get("description"),

                            calories=meal.get("calories"),

                            protein=meal.get("protein"),

                            carbs=meal.get("carbs"),

                            fat=meal.get("fat")

                        )


                        db.session.add(diet_meal)
                db.session.delete(temp_plan)

                db.session.commit()

        elif isinstance(ai_reply, dict) and ai_reply.get("intent") == "diet_plan_confirmation":


            plan = ai_reply.get("plan")

            if plan:
                TempDietPlan.query.filter_by(
                    user_id=user_id
                ).delete()

                temp = TempDietPlan(

                    user_id=user_id,

                    plan_data=plan

                )

                db.session.add(temp)

                db.session.commit()

        return jsonify({

            "success": True,

            "transcript": transcript,

            "reply": ai_reply,

            "audio_file": unique_filename

        }), 200

    except Exception as e:

        traceback.print_exc()


        return jsonify({

            "success": False,

            "message": str(e)

        }), 500
@chat.route("/chat/history", methods=["GET"])
@jwt_required()
def get_chat_history():

    user_id = get_jwt_identity()

    messages = (
        ChatMessage.query
        .filter_by(user_id=user_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    history = []

    for msg in messages:

        text = msg.message
        intent = None
        plan = None
        portion = None
        is_estimated = None

        if msg.sender == "ai":

            try:

                parsed = json.loads(msg.message)

                if isinstance(parsed, dict):

                    text = parsed.get("reply", msg.message)
                    intent = parsed.get("intent")
                    plan = parsed.get("plan")
                    portion = parsed.get("portion")
                    is_estimated = parsed.get("is_estimated")

            except Exception:
                pass

        history.append({

            "sender": msg.sender,
            "text": text,
            "intent": intent,
            "plan": plan,
            "portion": portion,
            "is_estimated": is_estimated,

            "image":
                f"http://127.0.0.1:5000/uploads/{msg.image_path}"
                if msg.image_path else None,

            "audio":
                f"http://127.0.0.1:5000/uploads/{msg.audio_path}"
                if msg.audio_path else None,

            "message_type": msg.message_type

        })

    return jsonify(history), 200

@chat.route("/chat/speak", methods=["POST"])
@jwt_required()
def speak():

    try:

        data = request.get_json()

        text = data.get("text")

        audio_file = generate_audio(text)

        return jsonify({
            "success": True,
            "audio": audio_file
        }),200

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "success":False,
            "message":str(e)
        }),500