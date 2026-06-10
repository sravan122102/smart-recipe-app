"""
Smart Recipe Suggestion System — Flask Application

Routes:
  GET  /                  → Serve the single-page app
  GET  /api/ingredients   → Return all ingredient names for autocomplete
  POST /api/find-recipes  → Run the full AI pipeline and return enriched recipes
  GET  /login             → Redirect to Google OAuth
  GET  /auth              → Google OAuth callback
  GET  /logout            → Log out user
  GET  /api/user          → Return current logged-in user data
  GET  /api/wishlist      → Get user's saved recipes
  POST /api/wishlist      → Save a recipe to the wishlist
"""

import os
import json
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from models import db, Ingredient, SearchCache, User, SavedRecipe
from ai_engine import process_pipeline


def create_app():
    """Application factory."""
    app = Flask(__name__)

    # Load configuration
    app.config.from_pyfile("config.py")

    # Initialize database
    db.init_app(app)

    # Initialize Authlib for Google Login
    oauth = OAuth(app)
    google = oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()
        
        # Seed the database with a massive list of ingredients
        massive_ingredients = [
            # Vegetables
            ("Tomato", "Vegetables"), ("Onion", "Vegetables"), ("Garlic", "Vegetables"), ("Potato", "Vegetables"),
            ("Carrot", "Vegetables"), ("Bell Pepper", "Vegetables"), ("Spinach", "Vegetables"), ("Broccoli", "Vegetables"),
            ("Cauliflower", "Vegetables"), ("Zucchini", "Vegetables"), ("Eggplant", "Vegetables"), ("Mushroom", "Vegetables"),
            ("Celery", "Vegetables"), ("Cabbage", "Vegetables"), ("Lettuce", "Vegetables"), ("Cucumber", "Vegetables"),
            ("Asparagus", "Vegetables"), ("Green Beans", "Vegetables"), ("Peas", "Vegetables"), ("Corn", "Vegetables"),
            ("Sweet Potato", "Vegetables"), ("Kale", "Vegetables"), ("Leek", "Vegetables"), ("Brussels Sprouts", "Vegetables"),
            ("Ginger", "Vegetables"), ("Scallion", "Vegetables"), ("Shallot", "Vegetables"), ("Radish", "Vegetables"),
            # Fruits
            ("Lemon", "Fruits"), ("Lime", "Fruits"), ("Apple", "Fruits"), ("Banana", "Fruits"),
            ("Orange", "Fruits"), ("Strawberry", "Fruits"), ("Blueberry", "Fruits"), ("Raspberry", "Fruits"),
            ("Avocado", "Fruits"), ("Pineapple", "Fruits"), ("Mango", "Fruits"), ("Peach", "Fruits"),
            ("Pear", "Fruits"), ("Grapes", "Fruits"), ("Watermelon", "Fruits"), ("Coconut", "Fruits"),
            # Meat & Poultry
            ("Chicken Breast", "Meat"), ("Chicken Thigh", "Meat"), ("Whole Chicken", "Meat"), ("Beef", "Meat"),
            ("Ground Beef", "Meat"), ("Steak", "Meat"), ("Pork", "Meat"), ("Bacon", "Meat"),
            ("Sausage", "Meat"), ("Lamb", "Meat"), ("Turkey", "Meat"), ("Ham", "Meat"),
            # Seafood
            ("Salmon", "Seafood"), ("Tuna", "Seafood"), ("Shrimp", "Seafood"), ("Crab", "Seafood"),
            ("Lobster", "Seafood"), ("Cod", "Seafood"), ("Tilapia", "Seafood"), ("Scallops", "Seafood"),
            ("Clams", "Seafood"), ("Mussels", "Seafood"), ("Squid", "Seafood"), ("Anchovy", "Seafood"),
            # Dairy & Eggs
            ("Eggs", "Dairy & Eggs"), ("Milk", "Dairy & Eggs"), ("Butter", "Dairy & Eggs"), ("Cheese", "Dairy & Eggs"),
            ("Cheddar Cheese", "Dairy & Eggs"), ("Mozzarella", "Dairy & Eggs"), ("Parmesan", "Dairy & Eggs"),
            ("Heavy Cream", "Dairy & Eggs"), ("Sour Cream", "Dairy & Eggs"), ("Yogurt", "Dairy & Eggs"),
            ("Cream Cheese", "Dairy & Eggs"), ("Feta Cheese", "Dairy & Eggs"), ("Ricotta", "Dairy & Eggs"),
            # Pantry & Grains
            ("Flour", "Pantry"), ("Whole Wheat Flour", "Pantry"), ("Wheat", "Pantry"), ("Sugar", "Pantry"), ("Brown Sugar", "Pantry"), ("Pasta", "Pantry"),
            ("Rice", "Pantry"), ("Brown Rice", "Pantry"), ("Noodles", "Pantry"), ("Oats", "Pantry"),
            ("Quinoa", "Pantry"), ("Bread", "Pantry"), ("Breadcrumbs", "Pantry"), ("Tortilla", "Pantry"),
            ("Lentils", "Pantry"), ("Black Beans", "Pantry"), ("Chickpeas", "Pantry"), ("Kidney Beans", "Pantry"),
            ("Honey", "Pantry"), ("Maple Syrup", "Pantry"), ("Peanut Butter", "Pantry"), ("Almonds", "Pantry"),
            ("Walnuts", "Pantry"), ("Pecans", "Pantry"), ("Cashews", "Pantry"), ("Chocolate Chips", "Pantry"),
            ("Cocoa Powder", "Pantry"), ("Vanilla Extract", "Pantry"), ("Baking Powder", "Pantry"), ("Baking Soda", "Pantry"),
            ("Yeast", "Pantry"), ("Cornstarch", "Pantry"),
            # Oils & Condiments
            ("Olive Oil", "Condiments"), ("Vegetable Oil", "Condiments"), ("Canola Oil", "Condiments"), ("Sesame Oil", "Condiments"),
            ("Soy Sauce", "Condiments"), ("Vinegar", "Condiments"), ("Balsamic Vinegar", "Condiments"), ("Apple Cider Vinegar", "Condiments"),
            ("Ketchup", "Condiments"), ("Mustard", "Condiments"), ("Mayonnaise", "Condiments"), ("Hot Sauce", "Condiments"),
            ("Worcestershire Sauce", "Condiments"), ("Fish Sauce", "Condiments"), ("Oyster Sauce", "Condiments"),
            ("Sriracha", "Condiments"), ("Barbecue Sauce", "Condiments"), ("Tomato Paste", "Condiments"),
            # Spices & Herbs
            ("Salt", "Spices"), ("Black Pepper", "Spices"), ("Paprika", "Spices"), ("Cumin", "Spices"),
            ("Cinnamon", "Spices"), ("Oregano", "Spices"), ("Basil", "Spices"), ("Thyme", "Spices"),
            ("Rosemary", "Spices"), ("Parsley", "Spices"), ("Cilantro", "Spices"), ("Chili Powder", "Spices"),
            ("Garlic Powder", "Spices"), ("Onion Powder", "Spices"), ("Nutmeg", "Spices"), ("Cloves", "Spices"),
            ("Turmeric", "Spices"), ("Coriander", "Spices"), ("Ginger Powder", "Spices"), ("Red Pepper Flakes", "Spices"),
            ("Bay Leaf", "Spices"), ("Curry Powder", "Spices"), ("Cardamom", "Spices"), ("Saffron", "Spices"),
            # Indian Essentials
            ("Ghee", "Dairy & Eggs"), ("Paneer", "Dairy & Eggs"), ("Curd", "Dairy & Eggs"), ("Yogurt", "Dairy & Eggs"),
            ("Toor Dal", "Pantry"), ("Moong Dal", "Pantry"), ("Masoor Dal", "Pantry"), ("Urad Dal", "Pantry"), ("Chana Dal", "Pantry"),
            ("Rajma", "Pantry"), ("Chole", "Pantry"), ("Kabuli Chana", "Pantry"), ("Black Eyed Peas", "Pantry"),
            ("Basmati Rice", "Pantry"), ("Atta", "Pantry"), ("Maida", "Pantry"), ("Besan", "Pantry"), ("Sooji", "Pantry"),
            ("Curry Leaves", "Herbs"), ("Mustard Seeds", "Spices"), ("Cumin Seeds", "Spices"), ("Asafoetida", "Spices"),
            ("Turmeric Powder", "Spices"), ("Red Chili Powder", "Spices"), ("Garam Masala", "Spices"), ("Coriander Powder", "Spices"),
            ("Kasuri Methi", "Spices"), ("Green Cardamom", "Spices"), ("Black Cardamom", "Spices"), ("Star Anise", "Spices"),
            ("Fennel Seeds", "Spices"), ("Tamarind", "Condiments"), ("Jaggery", "Pantry"), ("Coconut Milk", "Pantry"), ("Green Chilies", "Vegetables")
        ]
        
        # Only add ingredients that don't already exist in the database
        existing_ingredients = {i.name for i in Ingredient.query.with_entities(Ingredient.name).all()}
        new_items = []
        for name, category in massive_ingredients:
            if name not in existing_ingredients:
                new_items.append(Ingredient(name=name, category=category))
        
        if new_items:
            db.session.bulk_save_objects(new_items)
            db.session.commit()

    # ── Auth Routes ──────────────────────────────────────────────────────

    @app.route("/login")
    def login():
        """Redirect to Google Login."""
        redirect_uri = url_for('auth', _external=True)
        return google.authorize_redirect(redirect_uri)

    @app.route("/auth")
    def auth():
        """Google Login Callback."""
        token = google.authorize_access_token()
        userinfo = token.get('userinfo')
        if userinfo:
            email = userinfo['email']
            google_id = userinfo['sub']
            name = userinfo['name']

            # Check if user exists
            user = User.query.filter_by(google_id=google_id).first()
            if not user:
                # Create new user
                user = User(google_id=google_id, email=email, name=name)
                db.session.add(user)
                db.session.commit()
            
            login_user(user)
        return redirect(url_for('index'))

    @app.route("/logout")
    def logout():
        """Log out the user."""
        logout_user()
        return redirect(url_for('index'))

    @app.route("/api/user", methods=["GET"])
    def get_current_user():
        """Return current user info for frontend."""
        if current_user.is_authenticated:
            return jsonify({
                "is_authenticated": True,
                "name": current_user.name,
                "email": current_user.email
            })
        return jsonify({"is_authenticated": False})


    # ── Wishlist Routes ──────────────────────────────────────────────────

    @app.route("/api/wishlist", methods=["GET"])
    @login_required
    def get_wishlist():
        """Get all saved recipes for the current user."""
        saved = SavedRecipe.query.filter_by(user_id=current_user.id).order_by(SavedRecipe.created_at.desc()).all()
        recipes = []
        for s in saved:
            try:
                recipe_data = json.loads(s.recipe_json)
                recipe_data["saved_id"] = s.id
                recipes.append(recipe_data)
            except json.JSONDecodeError:
                pass
        return jsonify({"saved_recipes": recipes})

    @app.route("/api/wishlist", methods=["POST"])
    @login_required
    def save_recipe():
        """Save a recipe to the wishlist."""
        data = request.get_json()
        if not data or "recipe" not in data:
            return jsonify({"error": "Missing recipe data"}), 400
        
        recipe = data["recipe"]
        title = recipe.get("title", "Unknown Recipe")
        
        # Check if already saved
        existing = SavedRecipe.query.filter_by(user_id=current_user.id, recipe_title=title).first()
        if existing:
            return jsonify({"message": "Recipe already in wishlist"}), 200

        try:
            saved_recipe = SavedRecipe(
                user_id=current_user.id,
                recipe_json=json.dumps(recipe),
                recipe_title=title
            )
            db.session.add(saved_recipe)
            db.session.commit()
            return jsonify({"message": "Saved successfully", "saved_id": saved_recipe.id}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500


    # ── Core App Routes ──────────────────────────────────────────────────

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

        # Check cache first
        cache_key = "|".join(sorted(ingredients)).lower()
        cached = SearchCache.query.filter_by(ingredient_key=cache_key).first()

        if cached:
            # Use cache if less than 1 hour old
            cache_age = datetime.now(timezone.utc) - cached.created_at.replace(tzinfo=timezone.utc)
            if cache_age < timedelta(hours=1):
                return jsonify(json.loads(cached.result_json))

            # Stale cache — delete it
            try:
                db.session.delete(cached)
                db.session.commit()
            except Exception:
                db.session.rollback()

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
