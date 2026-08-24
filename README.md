🍽️ Kalorie AI

Kalorie AI is an AI-powered calorie tracking and nutrition multipurpose assistant web
application designed to help users track their meals, estimate calories and
macronutrients, monitor their daily nutrition progress, and receive
personalized nutrition assistance.

The application combines a React frontend, Flask backend, PostgreSQL
database, and OpenAI API to provide an interactive and personalized
nutrition tracking experience.

✨ Features

 🔐 User Authentication

- User registration
- User login
- Secure password handling
- JWT-based authentication
- Forgot password functionality
- Protected user-specific data

👤 Personalized User Profile

Users can create a personalized nutrition profile containing:

- Full name
- Age
- Gender
- Height
- Weight
- Activity level
- Fitness goal
- Dietary preferences
- Allergies

The profile information is used to provide more personalized calorie,
nutrition, and diet recommendations.

📸 AI-Powered Meal Analysis

Users can provide information about their meals to the AI assistant.

The AI can analyze food and provide estimated:

- Calories
- Protein
- Carbohydrates
- Fat
- Portion size

When an exact quantity is not available, the system can estimate the
portion size and provide estimated nutritional values.

📝 Meal Logging

Users can log meals and store their nutritional information.

Each meal can contain information such as:

- Meal name
- Calories
- Protein
- Carbohydrates
- Fat
- Portion
- Date and time

Meals are associated with the authenticated user and stored in the
database for future reference.
📊 Daily Nutrition Progress

The application tracks the user's daily nutritional intake.

Users can monitor:

- Daily calorie intake
- Protein consumption
- Carbohydrate consumption
- Fat consumption

Nutrition progress is displayed using visual charts to make the user's
daily intake easier to understand.

🍴 Meal History

Users can view their previously logged meals.

The stored meal history allows users to review their food intake over time
and provides the AI assistant with access to relevant previous meal
information.
🤖 AI Nutrition Assistant

Kalorie AI includes a conversational AI nutrition assistant.

Users can interact with the assistant using natural language to:

- Ask nutrition questions
- Ask about calories
- Log meals
- Ask about previously logged meals
- Get nutrition recommendations
- Ask about their daily intake
- Generate diet recommendations
- Discuss fitness and nutrition goals

Example questions:

How many calories are in this meal?

What did I eat today?

Show me my meal history.

How much protein did I consume today?

What should I eat for dinner?

Create a diet plan for me.

What is a good meal for weight loss?

🥗 Personalized Diet Plans
The AI assistant can generate meal and diet recommendations based on
information available in the user's profile and their fitness goals.
🎙️ Voice Interaction
The AI assistant supports voice-based interaction.
Users can record their voice, which is transcribed and processed by the
AI assistant.
AI responses can also be converted into speech for a more interactive
experience.
🛠️ Technology Stack
Frontend
•	React.js 
•	Vite 
•	JavaScript 
•	CSS 
Backend
•	Python 
•	Flask 
•	Flask-CORS 
•	Flask-JWT-Extended 
•	SQLAlchemy 
Database
•	PostgreSQL 
•	Neon PostgreSQL 
Artificial Intelligence
•	OpenAI API 
Deployment
•	Vercel for frontend deployment 
•	Cloud-based backend deployment 
•	Neon PostgreSQL for hosted database storage 

🏗️ Project Architecture
Kalorie AI follows a full-stack client-server architecture.
kalorie-app/
│
├── backend/
│   │
│   ├── database/
│   │   └── db.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── meal.py
│   │   ├── chat_message.py
│   │   └── diet_plan.py
│   │
│   ├── routes/
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── meals.py
│   │   ├── progress.py
│   │   └── ...
│   │
│   ├── services/
│   │   └── openai_service.py
│   │
│   ├── app.py
│   ├── config.py
│   ├── requirements.txt
│   └── .gitignore
│
├── frontend/
│   │
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── ...
│   │
│   ├── package.json
│   ├── vite.config.js
│   └── ...
│
└── README.md
🔄 How Kalorie AI Works
The application follows a client-server architecture where the React
frontend communicates with the Flask backend through API requests.
The backend handles authentication, business logic, AI communication,
database operations, and user-specific information.
                 ┌─────────────────┐
                 │      User       │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ React Frontend  │
                 │     + Vite      │
                 └────────┬────────┘
                          │
                     HTTP / API
                          │
                          ▼
                 ┌─────────────────┐
                 │ Flask Backend   │
                 │    REST API     │
                 └───────┬─────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
      ┌────────────────┐    ┌────────────────┐
      │  PostgreSQL    │    │   OpenAI API   │
      │    Database    │    │       AI       │
      └────────────────┘    └────────────────┘
🍴 Meal Logging Workflow
A typical meal logging process works as follows:
User provides meal information
             ↓
      React Frontend
             ↓
       Flask Backend
             ↓
        OpenAI API
             ↓
     Meal is analyzed
             ↓
Calories and macronutrients estimated
             ↓
      Meal stored in DB
             ↓
      Progress updated
             ↓
      Result shown to user
For image-based meal analysis, the AI can identify food items and estimate
their nutritional values.
If the exact portion is unknown, the system estimates the portion and
marks the nutritional information accordingly.

🤖 AI Architecture
The application uses the OpenAI API to provide AI-powered nutrition
functionality.
The backend contains an AI service responsible for communicating with
OpenAI and processing nutrition-related requests.
The AI assistant uses structured intents to determine what type of
nutrition-related operation the user is requesting.
Examples include:
•	Meal logging 
•	Meal updates 
•	Meal deletion 
•	Nutrition questions 
•	Meal history 
•	Diet plan generation 
•	General nutrition conversation 
This allows the AI assistant to perform different application actions
rather than only returning conversational responses.

🧠 AI Assistant Memory
The application uses different sources of information to provide
context-aware responses.
Short-Term Conversation Context
Recent chat messages are provided to the AI assistant so that it can
understand the current conversation.
Long-Term Meal History
Previously logged meals are stored in PostgreSQL and can be retrieved when
the user asks questions about their meal history.
For example:
When did I have halva?
The assistant can use the user's stored meal records to answer questions
about previous meals.

🧮 Calorie & Nutrition Tracking
The application uses user profile information to support personalized
nutrition recommendations.
The user's:
•	Age 
•	Gender 
•	Height 
•	Weight 
•	Activity level 
•	Fitness goal 
can be used when calculating calorie requirements and providing nutrition
recommendations.
The application supports calorie and macronutrient tracking for:
•	Calories 
•	Protein 
•	Carbohydrates 
•	Fat 
Daily progress is displayed through visual progress charts.
📈 Nutrition Progress
The progress section provides an overview of the user's daily nutritional
intake.
Users can compare their current intake with their nutritional targets.
The interface provides visual representations of:
•	Calories 
•	Protein 
•	Carbohydrates 
•	Fat 
This allows users to quickly understand how much of their daily nutrition
target they have consumed.
👤 User Profile
The profile system stores information used for personalized nutrition
assistance.
Example profile information:
Full Name: Example User
Age: 23
Gender: Male
Height: 175 cm
Weight: 60 kg
Activity Level: Sedentary
Fitness Goal: Weight Loss
Dietary Preference: Halal
Allergies: None
The AI assistant can use this information when generating relevant
nutrition recommendations.
🗄️ Database
PostgreSQL is used as the application's primary database.
The project uses SQLAlchemy as the Object Relational Mapper (ORM).
The database contains information related to:
Users
Stores user account and profile information.
Meals
Stores logged meals and their nutritional information.
Chat Messages
Stores conversations between users and the AI assistant.
Diet Plans
Stores generated or saved diet plan information.
The database allows information to persist between sessions.

🔐 Authentication & Security
The backend uses JWT-based authentication to protect user-specific
resources.
After authentication, requests to protected endpoints require a valid
JWT token.
This allows the backend to associate:
•	Meals 
•	Chat history 
•	Profile information 
•	Progress information 
with the correct authenticated user.
Sensitive credentials are stored using environment variables rather than
being included directly in the source code.

🔌 Backend API
The Flask backend exposes REST API endpoints for different parts of the
application.
Major API areas include:
Authentication
       ↓
User Profile
       ↓
Meal Management
       ↓
AI Chat
       ↓
Progress Tracking
       ↓
Diet Plans
The backend is responsible for validating requests, authenticating users,
processing AI requests, interacting with PostgreSQL, and returning
structured responses to the frontend.

⚙️ Installation & Setup
1. Clone the Repository
git clone https://github.com/hoorainfatimaaa/kalorie-app.git
Navigate into the project:
cd ai-calorie-app
🐍 Backend Setup
Navigate to the backend directory:
cd backend
Create a Python virtual environment:
python -m venv venv
Activate the virtual environment.
Windows
venv\Scripts\activate
Install the required dependencies:
pip install -r requirements.txt

🔑 Environment Variables
Create a .env file inside the backend directory.
Example:
DATABASE_URL=your_postgresql_database_url
OPENAI_API_KEY=your_openai_api_key
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret_key

▶️ Running the Backend
From the backend directory:
python app.py
The Flask development server will start locally.

