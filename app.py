"""
Smart Recipe Suggestion System — Flask Application

Routes:
  GET  /                  → Serve the single-page app
  GET  /api/ingredients   → Return all ingredient names for autocomplete
  POST /api/find-recipes  → Run the full AI pipeline and return enriched recipes
"""

import json
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request, jsonify
from models import db, Ingredient, SearchCache
from ai_engine import process_pipeline


def create_app():
    """Application factory."""
    app = Flask(__name__)

    # Load configuration
    app.config.from_pyfile("config.py")

    # Initialize database
    db.init_app(app)

    with app.app_context():
        db.create_all()

    # ── Routes ──────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        """Serve the main single-page application."""
        return render_template("index.html")

    @app.route("/api/ingredients", methods=["GET"])
    def get_ingredients():
        """Return all ingredient names grouped by category for autocomplete."""
        ingredients = Ingredient.query.order_by(Ingredient.name).all()

        # Group by category
        grouped = {}
        for ing in ingredients:
            grouped.setdefault(ing.category, []).append(ing.name)

        return jsonify({
            "ingredients": [ing.name for ing in ingredients],
            "grouped": grouped,
            "count": len(ingredients),
        })

    @app.route("/api/find-recipes", methods=["POST"])
    def find_recipes():
        """
        Run the full 5-module AI pipeline.

        Expects JSON body: {"ingredients": ["Onion", "Tomato", "Egg"]}
        Returns enriched recipe data with matching scores, missing ingredients,
        and substitution suggestions.
        """
        data = request.get_json()

        if not data or "ingredients" not in data:
            return jsonify({"error": "Missing 'ingredients' field"}), 400

        ingredients = data["ingredients"]

        if not isinstance(ingredients, list) or len(ingredients) < 2:
            return jsonify({
                "error": "Please provide at least 2 ingredients"
            }), 400

        # Clean and normalize ingredient names
        ingredients = [ing.strip().title() for ing in ingredients if ing.strip()]

        # Check cache first (cache key = sorted ingredient list)
        cache_key = "|".join(sorted(ingredients)).lower()
        cached = SearchCache.query.filter_by(ingredient_key=cache_key).first()

        if cached:
            # Use cache if less than 1 hour old
            cache_age = datetime.now(timezone.utc) - cached.created_at.replace(tzinfo=timezone.utc)
            if cache_age < timedelta(hours=1):
                return jsonify(json.loads(cached.result_json))

            # Stale cache — delete it
            db.session.delete(cached)
            db.session.commit()

        # Run the AI pipeline
        result = process_pipeline(ingredients)

        # Cache the result
        if result.get("recipes"):
            try:
                cache_entry = SearchCache(
                    ingredient_key=cache_key,
                    result_json=json.dumps(result),
                )
                db.session.add(cache_entry)
                db.session.commit()
            except Exception as e:
                print(f"[Cache] Failed to save: {e}")
                db.session.rollback()

        return jsonify(result)

    return app


# Create the global app instance for Vercel
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
