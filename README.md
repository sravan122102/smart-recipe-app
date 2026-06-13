# 🍳 Smart Recipe AI

An intelligent, AI-powered web application that acts as your personal chef. Tell the app what ingredients you have in your kitchen, and it will instantly generate tailored, step-by-step recipes utilizing exactly what you have on hand.

## ✨ Key Features

- **AI-Powered Culinary Engine**: Powered by Groq's lightning-fast LLaMA 3 8B model, the app generates creative, high-quality recipes with match scores, dynamic preparation times, and scalable servings.
- **Massive Ingredient Database**: Features an incredibly comprehensive database of nearly 400 ingredients, deeply covering everything from traditional South Indian staples (with native Tamil translations like *Vazhaipoo*) to modern international condiments (like *Gochujang* and *Miso Paste*).
- **Smart Autocomplete**: A highly responsive, typo-tolerant ingredient search interface that allows you to rapidly add items to your pantry or manually type custom ingredients.
- **Personalized Wishlist**: Create an account to securely save your favorite AI-generated recipes to your personal dashboard so you never lose a great meal idea.
- **Dynamic Servings Scaling**: Need to cook for 4 instead of 2? The app dynamically scales ingredient quantities based on your desired number of servings.
- **Beautiful, Modern UI**: A sleek, dark-mode-first aesthetic with micro-animations, progress rings, and mobile-responsive layout.

## 🛠️ Tech Stack

- **Backend**: Python, Flask, SQLAlchemy
- **Database**: SQLite
- **AI Integration**: Groq API (LLaMA 3 8B)
- **Frontend**: HTML5, Vanilla CSS, Vanilla JavaScript (Zero heavy UI frameworks)
- **Deployment**: Vercel Serverless

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- A Groq API Key

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sravan122102/smart-recipe-app.git
   cd smart-recipe-app
   ```

2. **Set up a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   Create a `.env` file in the root directory and add your Groq API key and a secret key for Flask sessions:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   SECRET_KEY=your_random_secret_key_here
   ```

5. **Run the Application:**
   ```bash
   python app.py
   ```

6. Open your browser and navigate to `http://127.0.0.1:5000/`.

## 📁 Project Structure

- `app.py`: The main Flask server containing API routes, database seeding, and user authentication logic.
- `ai_engine.py`: The prompt engineering and integration layer that safely communicates with the Groq API.
- `models.py`: SQLAlchemy database models for Users, Ingredients, and Saved Recipes.
- `static/js/app.js`: The frontend Single Page Application (SPA) logic handling dynamic rendering, local storage, and API interactions.
- `static/css/style.css`: The massive, beautifully structured stylesheet governing the modern UI.
- `templates/`: HTML templates served by Flask.

## 📄 License
This project is open-source and available for personal or educational use.
