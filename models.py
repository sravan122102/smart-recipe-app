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
