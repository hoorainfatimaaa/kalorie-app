from flask import Blueprint, request, jsonify
from models.user import User
from database.db import db
from flask_jwt_extended import create_access_token
import bcrypt
from flask_jwt_extended import jwt_required, get_jwt_identity

auth = Blueprint("auth", __name__)
@auth.route("/signup", methods=["POST"])
def signup():

    data = request.get_json()

    full_name = data.get("full_name")
    email = data.get("email")
    password = data.get("password")
    
    if not full_name or not email or not password:
        return jsonify({"message": "All fields are required"}), 400

    if len(full_name) < 2 or len(full_name) > 100:
       return jsonify({"error": "Full name must be between 2 and 100 characters."}), 400

    if any(not (c.isalpha() or c in " -'") for c in full_name):
       return jsonify({"error": "Full name can only contain letters, spaces, apostrophes, and hyphens."}), 400
   
    if len(full_name.split()) < 2:
       return jsonify({
        "error": "Please enter your first and last name."
    }), 400

    if not full_name or not email or not password:
        return jsonify({"message": "All fields are required"}), 400

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        return jsonify({"message": "Email already exists"}), 409

    hashed_password = bcrypt.hashpw(password.encode("utf-8"),bcrypt.gensalt()).decode("utf-8")

    new_user = User(
        full_name=full_name,
        email=email,
        password_hash=hashed_password
    )

    db.session.add(new_user)

    db.session.commit()

    access_token = create_access_token(
     identity=str(new_user.id)
)

    return jsonify({
    "message": "User registered successfully",
    "access_token": access_token
}), 201
    
@auth.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "message": "Email and password are required"
        }), 400

    existing_user = User.query.filter_by(email=email).first()

    if not existing_user:
        return jsonify({
            "message": "Invalid email or password"
        }), 401

    password_matches = bcrypt.checkpw(
        password.encode("utf-8"),
        existing_user.password_hash.encode("utf-8")
    )

    if not password_matches:
        return jsonify({
            "message": "Invalid email or password"
        }), 401

    access_token = create_access_token(
        identity=str(existing_user.id)
    )

    profile_completed = all([
    existing_user.age is not None,
    existing_user.gender is not None,
    existing_user.height is not None,
    existing_user.weight is not None,
    existing_user.activity_level is not None,
    existing_user.fitness_goal is not None
])

    return jsonify({
    "message": "Login successful",
    "access_token": access_token,
    "profile_completed": profile_completed
}), 200

@auth.route("/complete-profile", methods=["PUT"])
@jwt_required()
def complete_profile():

    current_user_id = int(get_jwt_identity())

    user = User.query.get(current_user_id)

    if not user:
        return jsonify({
            "message": "User not found"
        }), 404

    data = request.get_json()

    user.age = data.get("age")
    user.gender = data.get("gender")
    user.height = data.get("height")
    user.weight = data.get("weight")
    if not (1 <= user.age <= 120):
       return jsonify({"error": "Age must be between 15 and 120."}), 400

    if not (50 <= user.height <= 300):
       return jsonify({"error": "Height must be between 50 and 300 cm."}), 400

    if not (2 <= user.weight <= 500):
       return jsonify({"error": "Weight must be between 30 and 500 kg."}), 400
    user.activity_level = data.get("activity_level")
    user.fitness_goal = data.get("fitness_goal")
    user.dietary_preferences = data.get("dietary_preferences")
    user.allergies = data.get("allergies")

    db.session.commit()

    return jsonify({
        "message": "Profile updated successfully"
    }), 200