import os

# Groq API Configuration
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

# Flask Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "smart-recipe-suggestion-2025")
DEBUG = True

# Database Configuration
BASEDIR = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASEDIR, "recipes.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False
