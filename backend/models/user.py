from database.db import db
from datetime import datetime
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    full_name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)

    age = db.Column(db.Integer)


    gender = db.Column(db.String(20))

    height = db.Column(db.Float)

    weight = db.Column(db.Float)
    

    fitness_goal = db.Column(db.String(50))

    dietary_preferences = db.Column(db.Text)

    allergies = db.Column(db.Text)

    medical_condition = db.Column(db.Text)
    activity_level = db.Column(db.String(100))

    country = db.Column(db.String(100))

    region = db.Column(db.String(100))

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    meals = db.relationship(
    "Meal",
    backref="user",
    lazy=True,
    cascade="all, delete-orphan"
)
   