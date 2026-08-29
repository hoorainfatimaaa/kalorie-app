from database.db import db
from datetime import datetime
from pgvector.sqlalchemy import Vector
from services.embedding_service import EMBEDDING_DIMENSION


class UserMemory(db.Model):

    __tablename__ = "user_memories"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    memory_type = db.Column(db.String(50), nullable=False)
    memory_key = db.Column(db.String(100), nullable=False)
    memory_value = db.Column(db.Text, nullable=False)

    importance = db.Column(db.Integer, nullable=False, default=3)

    embedding = db.deferred(
        db.Column(Vector(EMBEDDING_DIMENSION), nullable=True)
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "memory_type", "memory_key",
            name="uq_user_memory_key"
        ),
    )
