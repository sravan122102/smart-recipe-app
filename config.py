import os

# Groq API Configuration
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "openai/gpt-oss-120b"

# Flask & Security Configuration
# Needs a strong secret key for session management and OAuth state
SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-default-key-change-me")
DEBUG = True

# Database Configuration
# Fallback to local SQLite if DATABASE_URL is not provided
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL", 
    "sqlite:///recipes.db"
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
