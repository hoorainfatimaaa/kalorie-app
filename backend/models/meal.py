from database.db import db
from datetime import datetime


class Meal(db.Model):

    __tablename__ = "meals"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    meal_name = db.Column(
        db.String(200),
        nullable=False
    )

    calories = db.Column(
        db.Float,
        nullable=False
    )

    protein = db.Column(
        db.Float,
        nullable=False
    )

    carbs = db.Column(
        db.Float,
        nullable=False
    )

    fat = db.Column(
        db.Float,
        nullable=False
    )
    portion = db.Column(
    db.String(255),
    nullable=True
)

    is_estimated = db.Column(
    db.Boolean,
    default=True
)

    image_path = db.Column(
        db.String(300),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
    chat_message_id = db.Column(
        db.Integer,
        db.ForeignKey("chat_messages.id"),
        nullable=True
    )
class UserMealContext(db.Model):

    __tablename__ = "user_meal_context"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        nullable=False
    )

    last_meal_id = db.Column(
        db.Integer,
        nullable=False
    )