from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from models.user import User
from database.db import db
profile = Blueprint("profile", __name__)
@profile.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():

    user_id = get_jwt_identity()

    user = User.query.get(user_id)

    return jsonify({
        "full_name": user.full_name,
        "email": user.email,
        "age": user.age,
        "gender": user.gender,
        "height": user.height,
        "weight": user.weight,
        "activity_level": user.activity_level,
        "fitness_goal": user.fitness_goal,
        "dietary_preferences": user.dietary_preferences,
        "allergies": user.allergies
    }), 200
@profile.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():

    user_id = get_jwt_identity()

    user = User.query.get(user_id)

    data = request.get_json()

    user.full_name = data["full_name"]
    user.age = data["age"]
    user.gender = data["gender"]
    user.height = data["height"]
    user.weight = data["weight"]
    user.activity_level = data["activity_level"]
    user.fitness_goal = data["fitness_goal"]
    user.dietary_preferences = data["dietary_preferences"]
    user.allergies = data["allergies"]

    db.session.commit()

    return jsonify({
        "message": "Profile updated successfully."
    }), 200