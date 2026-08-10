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
import re
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

NUTRITION_INTENTS = {
    "nutrition_question",
    "general_chat",
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


def build_nutrition_targets(user):
    """
    Backend-authoritative calorie/macro targets for the CURRENT user
    profile, computed via calculate_calorie_goal()/calculate_macro_goals()
    only — never invented anywhere else. Returns None if the profile is
    incomplete; callers must never substitute a guessed number in that
    case.
    """
    if not user_has_complete_profile(user):
        return None

    calorie_goal = calculate_calorie_goal(user)
    macros = calculate_macro_goals(user)

    return {
        "calorie_goal": calorie_goal,
        "protein_goal": macros["protein_goal"],
        "carbs_goal": macros["carbs_goal"],
        "fat_goal": macros["fat_goal"],
    }


def attach_nutrition_targets(ai_reply, user):
    """
    Attaches backend-calculated calorie/macro targets onto ai_reply for
    nutrition_question / general_chat — the free-form intents that
    apply_display_intent doesn't cover. Purely additive: never touches
    `reply` text. Ensures the caller/frontend always has the real
    numbers even if the AI's prose drifted (e.g. from stale
    conversation history).
    """
    if not isinstance(ai_reply, dict):
        return ai_reply

    if ai_reply.get("intent") not in NUTRITION_INTENTS:
        return ai_reply

    targets = build_nutrition_targets(user)
    if targets:
        ai_reply["calorie_goal"] = targets["calorie_goal"]
        ai_reply["protein_goal"] = targets["protein_goal"]
        ai_reply["carbs_goal"] = targets["carbs_goal"]
        ai_reply["fat_goal"] = targets["fat_goal"]

    return ai_reply


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


ALLOWED_PROFILE_FIELDS = {
    "full_name",
    "age",
    "gender",
    "height",
    "weight",
    "activity_level",
    "fitness_goal",
    "dietary_preferences",
    "allergies",
}

VALID_ACTIVITY_LEVELS = {
    "sedentary",
    "lightly_active",
    "moderately_active",
    "very_active",
    "extra_active",
}


VALID_FITNESS_GOALS = {
    "weight_loss",
    "weight_gain",
    "maintenance",
}


def validate_profile_updates(raw_updates):
    """
    Check the AI's proposed `updates` dict against the whitelist and
    per-field rules. Returns (valid_updates, rejected_fields) —
    rejected_fields maps field -> reason, for fields the AI proposed
    but that failed validation (used to build a clarification reply).
    Any field not in ALLOWED_PROFILE_FIELDS is silently dropped: the
    AI has no business proposing it (e.g. email, password, id).
    """
    valid_updates = {}
    rejected_fields = {}

    if not isinstance(raw_updates, dict):
        return valid_updates, rejected_fields

    for field, value in raw_updates.items():

        if field not in ALLOWED_PROFILE_FIELDS:
            continue

        if field in ("age", "height", "weight"):
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                rejected_fields[field] = "not_a_number"
                continue

            if field == "age" and not (1 <= numeric_value <= 120):
                rejected_fields[field] = "out_of_range"
                continue
            if field == "height" and not (30 <= numeric_value <= 300):
                rejected_fields[field] = "out_of_range"
                continue
            if field == "weight" and not (2 <= numeric_value <= 500):
                rejected_fields[field] = "out_of_range"
                continue

            valid_updates[field] = int(numeric_value) if field == "age" else numeric_value

        elif field == "activity_level":
            normalized = str(value).strip().lower().replace(" ", "_")
            if normalized not in VALID_ACTIVITY_LEVELS:
                rejected_fields[field] = "invalid_choice"
                continue
            valid_updates[field] = normalized

        elif field == "fitness_goal":
            normalized = str(value).strip().lower().replace(" ", "_")
            if normalized not in VALID_FITNESS_GOALS:
                rejected_fields[field] = "invalid_choice"
                continue
            valid_updates[field] = normalized

        else:
            # full_name, gender, dietary_preferences, allergies -> free text
            text_value = str(value).strip()
            if not text_value:
                rejected_fields[field] = "empty_value"
                continue
            valid_updates[field] = text_value

    return valid_updates, rejected_fields


ACTIVITY_LEVEL_ALIASES = {
    "extremely active": "extra_active",
    "extra active": "extra_active",
    "very active": "very_active",
    "moderately active": "moderately_active",
    "moderate activity": "moderately_active",
    "lightly active": "lightly_active",
    "light activity": "lightly_active",
    "sedentary": "sedentary",
}

FITNESS_GOAL_ALIASES = {
    "lose weight": "weight_loss",
    "losing weight": "weight_loss",
    "weight loss": "weight_loss",
    "gain weight": "weight_gain",
    "gaining weight": "weight_gain",
    "weight gain": "weight_gain",
    "build muscle": "weight_gain",
    "muscle gain": "weight_gain",
    "maintain my weight": "maintenance",
    "maintain weight": "maintenance",
    "maintenance": "maintenance",
}


FALLBACK_EXCLUDED_INTENTS = {
    "meal_log",
    "meal_update",
    "meal_delete",
    "save_diet_plan",
    "diet_plan_confirmation",
}

_QUESTION_START = re.compile(
    r"^(what|why|how|is|are|does|do|can|should|which|when|where)\b"
)


def extract_profile_updates_from_text(message, user):
    """
    Best-effort, conservative regex extraction of profile changes
    directly from the user's raw message. Returns a raw (unvalidated)
    updates dict — still passed through validate_profile_updates()
    before anything is applied.
    """
    if not message:
        return {}

    text = message.strip().lower()

    if not text or text.endswith("?") or _QUESTION_START.match(text):
        return {}

    updates = {}

    m = (
        re.search(r"weight.{0,15}?to\s+(\d+(?:\.\d+)?)\s*kg", text)
        or re.search(r"\bi'?m\s+(\d+(?:\.\d+)?)\s*kg\b", text)
        or re.search(r"\bmy\s+weight\s+is\s+(\d+(?:\.\d+)?)\s*kg?\b", text)
    )
    if m:
        updates["weight"] = m.group(1)

    m = (
        re.search(r"height.{0,15}?to\s+(\d+(?:\.\d+)?)\s*cm", text)
        or re.search(r"\bi'?m\s+(\d+(?:\.\d+)?)\s*cm\b", text)
    )
    if m:
        updates["height"] = m.group(1)

    m = (
        re.search(r"age.{0,15}?to\s+(\d+)\b", text)
        or re.search(r"\bi'?m\s+(\d+)\s*(?:years?\s*old|yo)\b", text)
    )
    if m:
        updates["age"] = m.group(1)

   
    if "activ" in text:
        for phrase, normalized in ACTIVITY_LEVEL_ALIASES.items():
            if phrase in text:
                updates["activity_level"] = normalized
                break

    for phrase, normalized in FITNESS_GOAL_ALIASES.items():
        if phrase in text:
            updates["fitness_goal"] = normalized
            break


    m = re.search(r"dietary preference.{0,15}?to\s+([a-z\- ]+)", text)
    if m:
        updates["dietary_preferences"] = m.group(1).strip()
    elif "vegetarian" in text and ("i'm" in text or "i am" in text or "im " in text):
        updates["dietary_preferences"] = "vegetarian"
    elif "vegan" in text and ("i'm" in text or "i am" in text or "im " in text):
        updates["dietary_preferences"] = "vegan"


    m = re.search(r"(?:change|update|set)\s+my\s+name\s+to\s+([a-z ]+)", text)
    if m:
        updates["full_name"] = m.group(1).strip().title()

    if "allerg" in text and not re.search(r"no longer allerg|remove", text):
        m = re.search(r"(?:i'?m|i am)\s+allerg(?:y|ic)\s+to\s+([a-z, ]+)", text)
        if not m:
            m = re.search(r"add\s+([a-z, ]+?)\s+allerg", text)
        if m:
            new_allergen = m.group(1).strip()
            existing = [a.strip() for a in (user.allergies or "").split(",") if a.strip()]
            if new_allergen and new_allergen.lower() not in [e.lower() for e in existing]:
                existing.append(new_allergen)
            updates["allergies"] = ", ".join(existing)

    if "allerg" in text and re.search(r"no longer allerg|remove", text):
        m = re.search(r"(?:no longer allerg(?:y|ic) to|remove)\s+(?:my\s+)?([a-z, ]+?)(?:\s+allerg(?:y|ies))?\b", text)
        if m:
            removed = m.group(1).strip()
            existing = [a.strip() for a in (user.allergies or "").split(",") if a.strip()]
            remaining = [a for a in existing if a.lower() != removed.lower()]
            updates["allergies"] = ", ".join(remaining)

    return updates
CONFIRMATION_WORDS = {
    "yes", "yeah", "yep", "yup", "sure", "ok", "okay", "confirm",
    "correct", "affirmative", "do it", "go ahead", "please do",
}


def is_bare_confirmation(message):
    text = (message or "").strip().lower().strip(".!")
    return text in CONFIRMATION_WORDS


_PENDING_NUMERIC_PATTERNS = [
    ("weight", re.compile(r"weight\s+to\s+(\d+(?:\.\d+)?)\s*kg", re.I)),
    ("height", re.compile(r"height\s+to\s+(\d+(?:\.\d+)?)\s*cm", re.I)),
    ("age", re.compile(r"age\s+to\s+(\d+)\b", re.I)),
]

_PENDING_ACTIVITY_PATTERN = re.compile(
    r"activity level to\s+([a-z ]+?)(?:\s*[\(\?]|$)", re.I
)
_PENDING_GOAL_PATTERN = re.compile(
    r"(?:fitness )?goal to\s+([a-z ]+?)(?:\s*[\(\?]|$)", re.I
)


def extract_pending_update_from_history(chat_history):
    """
    A bare 'yes'/'confirm' message carries no field or value itself.
    Scan the chat history backwards for the most recent AI message
    that proposed a specific profile change (e.g. "change your weight
    to 100 kg?") and pull the field/value it was proposing out of
    THAT message instead.
    """
    if not chat_history:
        return {}

    for chat_msg in reversed(chat_history):
        if chat_msg.sender != "ai":
            continue

        try:
            parsed = json.loads(chat_msg.message)
            text = parsed.get("reply", "") if isinstance(parsed, dict) else chat_msg.message
        except Exception:
            text = chat_msg.message

        if not text:
            continue

        lower = text.lower()

        for field, pattern in _PENDING_NUMERIC_PATTERNS:
            m = pattern.search(lower)
            if m:
                return {field: m.group(1)}

        m = _PENDING_ACTIVITY_PATTERN.search(lower)
        if m:
            return {"activity_level": m.group(1).strip()}

        m = _PENDING_GOAL_PATTERN.search(lower)
        if m:
            return {"fitness_goal": m.group(1).strip()}

    
        break

    return {}

def apply_profile_update(ai_reply, user, message="", chat_history=None):
    """
    Applies profile changes to the authenticated user's row.

    Primary path: ai_reply["intent"] == "update_profile" with a valid
    "updates" dict — validated and applied as before.

    Fallback path: if the AI didn't produce a usable update (asked for
    confirmation, returned empty updates, or misclassified the intent
    as general_chat), a conservative regex pass over the raw user
    `message` is used instead, so a clear command like "change my
    weight to 65kg" still updates the database in this same turn
    regardless of what the AI decided to say back.

    After a successful commit, recalculates the user's calorie and
    macro targets using the existing nutrition_service functions
    (calculate_calorie_goal / calculate_macro_goals) — these are the
    single authoritative source, never invented here or by the AI —
    and attaches them to ai_reply along with an updated confirmation
    reply. If the profile is still incomplete after the update, no
    targets are returned and the reply explains what's missing
    instead.

    Mutates and returns ai_reply. No-op if neither path applies
    (e.g. this was a meal_log/nutrition_question/etc. message).
    """
    if not isinstance(ai_reply, dict):
        return ai_reply

    intent = ai_reply.get("intent")
    is_declared_update = intent == "update_profile"
    print("PROFILE DEBUG - AI INTENT:", intent)
    print("PROFILE DEBUG - MESSAGE:", message)
    print("PROFILE DEBUG - AI UPDATES:", ai_reply.get("updates"))

    raw_updates = ai_reply.get("updates") if is_declared_update else None
    valid_updates, rejected_fields = validate_profile_updates(raw_updates or {})

    used_fallback = False
    if not valid_updates and intent not in FALLBACK_EXCLUDED_INTENTS:

        if is_bare_confirmation(message):
           
            fallback_raw = extract_pending_update_from_history(chat_history)
        else:
            fallback_raw = extract_profile_updates_from_text(message, user)

        if fallback_raw:
            fallback_valid, _ = validate_profile_updates(fallback_raw)
            if fallback_valid:
                valid_updates = fallback_valid
                used_fallback = True

    if not valid_updates and message.strip().lower() in {
    "yes",
    "yes please",
    "yeah",
    "yep",
    "sure",
    "okay",
    "ok",
    "confirm",
    "confirmed"
}:
        if chat_history:
            for previous_message in reversed(chat_history):

                if previous_message.sender != "ai":
                    continue

                try:
                    previous_ai = json.loads(previous_message.message)

                    if not isinstance(previous_ai, dict):
                        continue

                    previous_updates = previous_ai.get("updates")

                    if previous_updates:
                        previous_valid, _ = validate_profile_updates(
                        previous_updates
                    )

                        if previous_valid:
                            valid_updates = previous_valid
                            used_fallback = True
                            break

                except (json.JSONDecodeError, TypeError):
                    continue
    print("PROFILE DEBUG - FALLBACK USED:", used_fallback)
    print("PROFILE DEBUG - VALID UPDATES:", valid_updates)
    if not is_declared_update and not used_fallback:
        
        return ai_reply

    if valid_updates:
    
        for field, value in valid_updates.items():
            setattr(user, field, value)
        db.session.commit()

        changed = ", ".join(f.replace("_", " ") for f in valid_updates)
        ai_reply["intent"] = "update_profile"
        ai_reply["updates"] = valid_updates

        if user_has_complete_profile(user):
            
            calorie_goal = calculate_calorie_goal(user)
            macros = calculate_macro_goals(user)

            ai_reply["calorie_goal"] = calorie_goal
            ai_reply["protein_goal"] = macros["protein_goal"]
            ai_reply["carbs_goal"] = macros["carbs_goal"]
            ai_reply["fat_goal"] = macros["fat_goal"]

            ai_reply["reply"] = (
                f"Your {changed} has been updated.\n\n"
                "Your daily nutrition targets have also been recalculated:\n\n"
                f"- Calories: {calorie_goal} kcal\n"
                f"- Protein: {macros['protein_goal']} g\n"
                f"- Carbs: {macros['carbs_goal']} g\n"
                f"- Fat: {macros['fat_goal']} g"
            )
        else:
         
            missing = [
                name for name, val in [
                    ("age", user.age),
                    ("height", user.height),
                    ("weight", user.weight),
                    ("gender", user.gender),
                    ("fitness goal", user.fitness_goal),
                ]
                if val is None
            ]
            ai_reply["calorie_goal"] = None
            ai_reply["protein_goal"] = None
            ai_reply["carbs_goal"] = None
            ai_reply["fat_goal"] = None
            ai_reply["reply"] = (
                f"Your {changed} has been updated. I still need your "
                + ", ".join(missing)
                + " to calculate your daily calorie and macro targets."
            )
        print("PROFILE UPDATE SUCCESS")
        print("UPDATED FIELDS:", valid_updates)
        print("FINAL INTENT:", ai_reply.get("intent"))
        print("NEW WEIGHT:", user.weight)
        print("NEW FITNESS GOAL:", user.fitness_goal)
        return ai_reply

    if is_declared_update:
        if rejected_fields:
           
            bad_field = next(iter(rejected_fields)).replace("_", " ")
            ai_reply["reply"] = (
                f"That doesn't look like a valid value for {bad_field}. "
                "Please try again."
            )
   
        ai_reply["updates"] = {}

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
        nutrition_targets = build_nutrition_targets(user)

        ai_reply = ask_openai(
        message=message,
        image=image,
        user=user,
        meals=meals,
        chat_history=chat_history,
        current_plan=current_plan,
        nutrition_targets=nutrition_targets
)
        print("AI BEFORE PROFILE UPDATE:", ai_reply)

        ai_reply = apply_profile_update(ai_reply, user, message,chat_history)

        print("AI AFTER PROFILE UPDATE:", ai_reply)

   
        user = User.query.get(user_id)

        ai_reply = apply_display_intent(ai_reply, user, user_id, current_plan)
        ai_reply = attach_nutrition_targets(ai_reply, user)

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

   
        nutrition_targets = build_nutrition_targets(user)

        ai_reply = ask_openai(
            message=transcript,
            image=None,
            user=user,
            meals=meals,
            chat_history=chat_history,
            current_plan=current_plan,
            nutrition_targets=nutrition_targets
        )

     
        ai_reply = apply_profile_update(ai_reply, user, transcript,chat_history)

        user = User.query.get(user_id)

        ai_reply = apply_display_intent(ai_reply, user, user_id, current_plan)
        ai_reply = attach_nutrition_targets(ai_reply, user)

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