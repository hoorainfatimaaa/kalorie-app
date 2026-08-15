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
