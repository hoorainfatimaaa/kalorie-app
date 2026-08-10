from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from datetime import date
from database.db import db

from models.user import User
from models.meal import Meal

from services.nutrition_service import calculate_macro_goals,calculate_calorie_goal

progress = Blueprint("progress", __name__)


@progress.route("/progress", methods=["GET"])
@jwt_required()
def get_progress():

    try:

        user_id = get_jwt_identity()

        user = User.query.get(user_id)

        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404

    
        calorie_goal = calculate_calorie_goal(user)
        macro_goals = calculate_macro_goals(user)

        today = date.today()

        meals = Meal.query.filter(
            Meal.user_id == user_id,
            db.func.date(Meal.created_at) == today
        ).all()

        calories = sum(meal.calories or 0 for meal in meals)
        protein = sum(meal.protein or 0 for meal in meals)
        carbs = sum(meal.carbs or 0 for meal in meals)
        fat = sum(meal.fat or 0 for meal in meals)

        return jsonify({

            "success": True,

            "calories": round(calories),
            "calorieGoal": calorie_goal,

            "protein": round(protein),
            "proteinGoal": macro_goals["protein_goal"],

            "carbs": round(carbs),
            "carbsGoal": macro_goals["carbs_goal"],

            "fat": round(fat),
            "fatGoal": macro_goals["fat_goal"]

        }), 200

    except Exception as e:

        print("PROGRESS ERROR:", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500