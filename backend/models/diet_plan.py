from database.db import db
from datetime import datetime


class DietPlan(db.Model):

    __tablename__ = "diet_plans"


    id = db.Column(
        db.Integer,
        primary_key=True
    )


    user_id = db.Column(
        db.Integer,
        nullable=False
    )


    day = db.Column(
        db.String(20),
        nullable=False
    )


    meal_type = db.Column(
        db.String(30),
        nullable=False
    )


    meal_name = db.Column(
        db.String(100),
        nullable=False
    )


    description = db.Column(
        db.Text
    )


    calories = db.Column(
        db.Float
    )


    protein = db.Column(
        db.Float
    )


    carbs = db.Column(
        db.Float
    )


    fat = db.Column(
        db.Float
    )


    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )