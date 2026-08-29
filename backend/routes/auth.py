from flask import Blueprint, request, jsonify
from models.user import User
from models.password_reset import PasswordResetToken
from database.db import db
from flask_jwt_extended import create_access_token
import bcrypt
import os
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.openai_service import validate_country_region
from services.email_service import send_password_reset_email

auth = Blueprint("auth", __name__)

MIN_PASSWORD_LENGTH = 8
@auth.route("/signup", methods=["POST"])
def signup():

    data = request.get_json()

    full_name = data.get("full_name")
    email = data.get("email")
    password = data.get("password")
    
    if not full_name or not email or not password:
        return jsonify({"message": "All fields are required"}), 400

    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify({
            "message": "Password must be at least %d characters long."
                       % MIN_PASSWORD_LENGTH
        }), 400

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

    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify({
            "message": "Password must be at least %d characters long."
                       % MIN_PASSWORD_LENGTH
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
    existing_user.fitness_goal is not None,
    bool((existing_user.dietary_preferences or "").strip()),
    bool((existing_user.allergies or "").strip()),
    bool((existing_user.medical_condition or "").strip()),
    bool((existing_user.country or "").strip()),
    bool((existing_user.region or "").strip())
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

    dietary_preferences = (data.get("dietary_preferences") or "").strip()
    allergies = (data.get("allergies") or "").strip()
    medical_condition = (data.get("medical_condition") or "").strip()

    if not dietary_preferences:
        return jsonify({"error": "Dietary preferences are required , enter \"None\" if not applicable."}), 400

    if not allergies:
        return jsonify({"error": "Allergies are required , enter \"None\" if not applicable."}), 400

    if not medical_condition:
        return jsonify({"error": "Medical condition is required , enter \"None\" if not applicable."}), 400

    country = (data.get("country") or "").strip()
    region = (data.get("region") or "").strip()

    if not country:
        return jsonify({"error": "Country is required."}), 400

    if not region:
        return jsonify({"error": "Region is required."}), 400

    region_check = validate_country_region(country, region)

    if not region_check.get("consistent", True):

        return jsonify({
            "error": region_check.get("reason")
            or f"\"{region}\" is not in {country} — please enter a region inside {country}."
        }), 400

    user.activity_level = data.get("activity_level")
    user.fitness_goal = data.get("fitness_goal")
    user.dietary_preferences = dietary_preferences
    user.allergies = allergies
    user.medical_condition = medical_condition
    user.country = country
    user.region = region

    db.session.commit()

    return jsonify({
        "message": "Profile updated successfully"
    }), 200


logger = logging.getLogger(__name__)

RESET_TOKEN_EXPIRY_MINUTES = int(os.getenv("RESET_TOKEN_EXPIRY_MINUTES", "30"))

RESET_REQUEST_COOLDOWN_SECONDS = int(
    os.getenv("RESET_REQUEST_COOLDOWN_SECONDS", "60")
)

RESET_REQUESTED_MESSAGE = (
    "If an account exists for that email, a password reset link has "
    "been sent. Please check your inbox."
)


def hash_reset_token(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@auth.route("/forgot-password", methods=["POST"])
def forgot_password():

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"message": "Email is required"}), 400

    user = User.query.filter(db.func.lower(User.email) == email).first()

    if user is None:
        return jsonify({"message": RESET_REQUESTED_MESSAGE}), 200

    recent = (
        PasswordResetToken.query
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.created_at >= datetime.utcnow() - timedelta(
                seconds=RESET_REQUEST_COOLDOWN_SECONDS
            )
        )
        .first()
    )

    if recent:
        return jsonify({"message": RESET_REQUESTED_MESSAGE}), 200

    PasswordResetToken.query.filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None)
    ).delete(synchronize_session=False)

    raw_token = secrets.token_urlsafe(32)

    db.session.add(PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(
            minutes=RESET_TOKEN_EXPIRY_MINUTES
        )
    ))
    db.session.commit()

    send_password_reset_email(
        user.email, user.full_name, raw_token, RESET_TOKEN_EXPIRY_MINUTES
    )

    return jsonify({"message": RESET_REQUESTED_MESSAGE}), 200


@auth.route("/reset-password/validate", methods=["POST"])
def validate_reset_token():

    data = request.get_json(silent=True) or {}
    raw_token = (data.get("token") or "").strip()

    if not raw_token:
        return jsonify({"valid": False, "message": "Reset token is required"}), 400

    record = PasswordResetToken.query.filter_by(
        token_hash=hash_reset_token(raw_token)
    ).first()

    if record is None or not record.is_usable():
        return jsonify({
            "valid": False,
            "message": "This reset link is invalid or has expired."
        }), 400

    return jsonify({"valid": True}), 200


@auth.route("/reset-password", methods=["POST"])
def reset_password():

    data = request.get_json(silent=True) or {}
    raw_token = (data.get("token") or "").strip()
    password = data.get("password") or ""

    if not raw_token or not password:
        return jsonify({"message": "Reset token and new password are required"}), 400

    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify({
            "message": "Password must be at least %d characters long."
                       % MIN_PASSWORD_LENGTH
        }), 400

    record = PasswordResetToken.query.filter_by(
        token_hash=hash_reset_token(raw_token)
    ).first()

    if record is None or not record.is_usable():
        return jsonify({
            "message": "This reset link is invalid or has expired. "
                       "Please request a new one."
        }), 400

    user = User.query.get(record.user_id)

    if user is None:
        return jsonify({
            "message": "This reset link is invalid or has expired. "
                       "Please request a new one."
        }), 400

    user.password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    record.used_at = datetime.utcnow()

    PasswordResetToken.query.filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.id != record.id,
        PasswordResetToken.used_at.is_(None)
    ).delete(synchronize_session=False)

    db.session.commit()

    logger.info("Password reset completed for user %s", user.id)

    return jsonify({
        "message": "Your password has been reset. You can now log in."
    }), 200
