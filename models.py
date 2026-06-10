from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class Ingredient(db.Model):
    """Master ingredients list for autocomplete."""
    __tablename__ = "ingredients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, default="Other")

    def __repr__(self):
        return f"<Ingredient {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
        }


class SearchCache(db.Model):
    """Cache recent AI search results to reduce API calls."""
    __tablename__ = "search_cache"

    id = db.Column(db.Integer, primary_key=True)
    ingredient_key = db.Column(db.String(500), unique=True, nullable=False, index=True)
    result_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<SearchCache {self.ingredient_key[:40]}>"


from flask_login import UserMixin

class User(db.Model, UserMixin):
    """User account model for Google Login."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship to saved recipes
    saved_recipes = db.relationship('SavedRecipe', backref='user', lazy=True)


class SavedRecipe(db.Model):
    """Stores recipes a user has saved to their wishlist."""
    __tablename__ = "saved_recipes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Store the exact recipe JSON so it looks exactly as generated
    recipe_json = db.Column(db.Text, nullable=False)
    recipe_title = db.Column(db.String(200), nullable=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
