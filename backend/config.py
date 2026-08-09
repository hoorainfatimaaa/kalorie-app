import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

print("DATABASE_URL EXISTS:", bool(DATABASE_URL))
print("DATABASE_URL START:", DATABASE_URL[:30] if DATABASE_URL else "MISSING")
print("DATABASE_URL HAS_NONE:", "None" in DATABASE_URL if DATABASE_URL else False)


class Config:
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)