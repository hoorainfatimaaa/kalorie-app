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
from sqlalchemy import func
from datetime import date
import json
chat = Blueprint("chat", __name__)
def clean_text(value):
    if isinstance(value, str):
        return value.replace("\x00", "")
    return value
today = date.today()
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