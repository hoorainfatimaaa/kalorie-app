from database.db import db
from datetime import datetime


class ConversationSummary(db.Model):

    __tablename__ = "conversation_summaries"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    summary = db.Column(db.Text, nullable=False, default="")

    summarized_message_count = db.Column(db.Integer, nullable=False, default=0)

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
