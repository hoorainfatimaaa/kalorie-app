from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.meal import Meal
from database.db import db

meals = Blueprint("meals", __name__)


@meals.route("/meal-history", methods=["GET"])
@jwt_required()
def meal_history():

    user_id = get_jwt_identity()

    meals = Meal.query.filter_by(
        user_id=user_id
    ).order_by(
        Meal.created_at.desc()
    ).limit(100).all()


    result = []

    for meal in meals:

        result.append({

            "id": meal.id,

            "meal_name": meal.meal_name,

            "calories": meal.calories,

            "protein": meal.protein,

            "carbs": meal.carbs,

            "fat": meal.fat,

            "date": meal.created_at.strftime(
                "%d %B %Y"
            ),

            "time": meal.created_at.strftime(
                "%I:%M %p"
            )

        })


    return jsonify(result)

@meals.route("/meals/<int:meal_id>", methods=["DELETE"])
@jwt_required()
def delete_meal(meal_id):
    try:
        user_id = get_jwt_identity()

        meal = Meal.query.filter_by(
            id=meal_id,
            user_id=user_id
        ).first()

        if not meal:
            return jsonify({"message": "Meal not found"}), 404

        db.session.delete(meal)
        db.session.commit()

        return jsonify({"message": "Meal deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": str(e)}), 500