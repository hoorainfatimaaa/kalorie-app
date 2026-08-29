import time
from sqlalchemy.exc import OperationalError
from flask import Flask
from flask_cors import CORS
from config import Config
from database.db import db
from models.user import User
from routes.auth import auth
from flask_jwt_extended import JWTManager
from routes.chat import chat
from models.meal import Meal
from models.chat_message import ChatMessage
from flask import send_from_directory
from models.diet_plan import DietPlan
from models.conversation_summary import ConversationSummary
from models.user_memory import UserMemory
from models.password_reset import PasswordResetToken
app = Flask(__name__)

app.config.from_object(Config)
CORS(app, origins=[
    "http://localhost:5173",
    "https://kalorie-app-sage.vercel.app"
])
db.init_app(app)
jwt = JWTManager(app)
app.register_blueprint(auth)
app.register_blueprint(chat)
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory("uploads", filename)
with app.app_context():
    for attempt in range(5):
        try:
            db.create_all()
            break
        except OperationalError:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)

@app.route("/")
def home():
    return "Backend working"

if __name__ == "__main__":
    app.run(debug=True)