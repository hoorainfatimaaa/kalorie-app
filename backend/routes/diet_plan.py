from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.diet_plan import DietPlan


diet = Blueprint("diet",__name__)


@diet.route("/diet-plan", methods=["GET"])
@jwt_required()
def get_diet_plan():

    user_id = get_jwt_identity()


    meals = DietPlan.query.filter_by(
        user_id=user_id
    ).all()


    plan = {}


    for meal in meals:

        if meal.day not in plan:
            plan[meal.day] = []


        plan[meal.day].append({

            "meal_type": meal.meal_type,

            "meal_name": meal.meal_name,

            "description": meal.description,

            "calories": meal.calories,

            "protein": meal.protein,

            "carbs": meal.carbs,

            "fat": meal.fat

        })


    return jsonify(plan), 200