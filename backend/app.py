from flask import Flask
from flask_cors import CORS
from config import Config
from database.db import db
from models.user import User
from routes.auth import auth
from flask_jwt_extended import JWTManager
from routes.chat import chat
from models.meal import Meal
from routes.progress import progress
from models.chat_message import ChatMessage
from flask import send_from_directory
from routes.profile import profile
from routes.meals import meals
from models.diet_plan import DietPlan
from routes.diet_plan import diet
app = Flask(__name__)

app.config.from_object(Config)

CORS(app, origins=["https://kalorie-app-sage.vercel.app"])
db.init_app(app)
jwt = JWTManager(app)
app.register_blueprint(auth)
app.register_blueprint(chat)
app.register_blueprint(progress)
app.register_blueprint(profile)
app.register_blueprint(meals)
app.register_blueprint(diet)
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory("uploads", filename)
with app.app_context():
    db.create_all()

@app.route("/")
def home():
    return "Backend working"

if __name__ == "__main__":
    app.run(debug=True)