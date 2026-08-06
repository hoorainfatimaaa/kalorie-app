from database.db import db
from datetime import datetime


class ChatMessage(db.Model):

    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    sender = db.Column(
        db.String(10),
        nullable=False
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
    message_type = db.Column(
    db.String(20),
    default="text"
    )
    image_path = db.Column(db.String(255))
    audio_path = db.Column(db.String(255))
    meal = db.relationship(
        "Meal",
        backref="chat_message",
        uselist=False
    )
    