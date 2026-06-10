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
            # RICE VARIETIES
            ("Basmati Rice", "Pantry"), ("Sona Masoori Rice", "Pantry"), ("Ponni Rice", "Pantry"),
            ("Seeraga Samba Rice", "Pantry"), ("Idli Rice (Puzhungal)", "Pantry"), ("Kolam Rice", "Pantry"),
            ("Gobindobhog Rice", "Pantry"), ("Jeera Samba Rice", "Pantry"), ("Matta Rice", "Pantry"),
            ("Bamboo Rice", "Pantry"), ("Kali Jeera Rice", "Pantry"), ("Red Rice", "Pantry"),

            # WHEAT & FLOUR
            ("Wheat (Godhumai)", "Pantry"), ("Maida (All Purpose)", "Pantry"), ("Atta (Whole Wheat)", "Pantry"),
            ("Semolina (Sooji/Rava)", "Pantry"), ("Rice Flour", "Pantry"), ("Corn Flour", "Pantry"),
            ("Besan (Chickpea Flour)", "Pantry"), ("Ragi Flour", "Pantry"), ("Bajra Flour", "Pantry"),
            ("Jowar Flour", "Pantry"), ("Idiyappam Flour", "Pantry"), ("Puttu Flour", "Pantry"),

            # LENTILS & DALS
            ("Toor Dal", "Pantry"), ("Moong Dal", "Pantry"), ("Urad Dal", "Pantry"),
            ("Chana Dal", "Pantry"), ("Masoor Dal", "Pantry"), ("Rajma (Kidney Beans)", "Pantry"),
            ("Kabuli Chana (White Chickpea)", "Pantry"), ("Kala Chana (Black Chickpea)", "Pantry"),
            ("Moth Beans", "Pantry"), ("Horsegram (Kollu)", "Pantry"), ("Cowpea (Lobia)", "Pantry"),
            ("Whole Moong", "Pantry"), ("Whole Urad", "Pantry"), ("Val Dal", "Pantry"),

            # VEGETABLES
            ("Onion", "Vegetables"), ("Tomato", "Vegetables"), ("Potato", "Vegetables"),
            ("Brinjal / Eggplant", "Vegetables"), ("Drumstick (Murungakkai)", "Vegetables"),
            ("Raw Banana", "Vegetables"), ("Plantain Stem", "Vegetables"), ("Plantain Flower", "Vegetables"),
            ("Bitter Gourd", "Vegetables"), ("Snake Gourd", "Vegetables"), ("Ridge Gourd", "Vegetables"),
            ("Bottle Gourd (Lauki)", "Vegetables"), ("Ash Gourd", "Vegetables"), ("Ivy Gourd (Kovakkai)", "Vegetables"),
            ("Raw Jackfruit", "Vegetables"), ("Yam (Senai Kizhangu)", "Vegetables"), ("Elephant Foot Yam", "Vegetables"),
            ("Colocasia (Arbi)", "Vegetables"), ("Sweet Potato", "Vegetables"), ("Raw Mango", "Vegetables"),
            ("Raw Papaya", "Vegetables"), ("Carrot", "Vegetables"), ("Beans (French Beans)", "Vegetables"),
            ("Cluster Beans", "Vegetables"), ("Broad Beans", "Vegetables"), ("Capsicum", "Vegetables"),
            ("Cauliflower", "Vegetables"), ("Cabbage", "Vegetables"), ("Broccoli", "Vegetables"),
            ("Spinach (Palak)", "Vegetables"), ("Fenugreek Leaves (Methi)", "Vegetables"),
            ("Drumstick Leaves", "Vegetables"), ("Amaranth Leaves", "Vegetables"), ("Curry Leaves", "Vegetables"),
            ("Coriander Leaves", "Vegetables"), ("Mint Leaves", "Vegetables"), ("Spring Onion", "Vegetables"),
            ("Leek", "Vegetables"), ("Radish (Mullangi)", "Vegetables"), ("Turnip", "Vegetables"),
            ("Beetroot", "Vegetables"), ("Pumpkin", "Vegetables"), ("Corn / Maize", "Vegetables"),
            ("Peas", "Vegetables"), ("Lady's Finger (Okra)", "Vegetables"), ("Tindora", "Vegetables"),
            ("Raw Turmeric", "Vegetables"), ("Garlic", "Vegetables"), ("Ginger", "Vegetables"),
            ("Green Chilli", "Vegetables"), ("Shallots", "Vegetables"),

            # FRUITS
            ("Mango", "Fruits"), ("Banana", "Fruits"), ("Coconut", "Fruits"), ("Tamarind", "Fruits"),
            ("Lemon", "Fruits"), ("Lime", "Fruits"), ("Amla", "Fruits"), ("Guava", "Fruits"),
            ("Papaya", "Fruits"), ("Pineapple", "Fruits"), ("Jackfruit", "Fruits"), ("Watermelon", "Fruits"),
            ("Pomegranate", "Fruits"), ("Dates", "Fruits"), ("Kokum", "Fruits"), ("Bael Fruit", "Fruits"),
            ("Wood Apple", "Fruits"), ("Star Fruit", "Fruits"),

            # SPICES (WHOLE)
            ("Cumin Seeds (Jeera)", "Spices"), ("Mustard Seeds (Kadugu)", "Spices"), ("Fenugreek Seeds (Methi)", "Spices"),
            ("Coriander Seeds (Dhania)", "Spices"), ("Black Pepper", "Spices"), ("Red Chilli (Dried)", "Spices"),
            ("Cloves (Lavang)", "Spices"), ("Cardamom Green (Elaichi)", "Spices"), ("Black Cardamom", "Spices"),
            ("Cinnamon (Dalchini)", "Spices"), ("Bay Leaf (Tejpatta)", "Spices"), ("Star Anise", "Spices"),
            ("Mace (Javitri)", "Spices"), ("Nutmeg (Jaiphal)", "Spices"), ("Fennel Seeds (Saunf)", "Spices"),
            ("Carom Seeds (Ajwain)", "Spices"), ("Nigella Seeds (Kalonji)", "Spices"), ("Poppy Seeds", "Spices"),
            ("Sesame Seeds (Til)", "Spices"), ("Turmeric (Manjal)", "Spices"), ("Dry Ginger (Sukku)", "Spices"),
            ("Long Pepper (Thippili)", "Spices"), ("Kalpasi (Stone Flower)", "Spices"), ("Marathi Mokku", "Spices"),
            ("Dried Rose Petals", "Spices"), ("Saffron (Kesar)", "Spices"),

            # SPICE POWDERS
            ("Turmeric Powder", "Spices"), ("Red Chilli Powder", "Spices"), ("Coriander Powder", "Spices"),
            ("Cumin Powder", "Spices"), ("Garam Masala", "Spices"), ("Sambar Powder", "Spices"),
            ("Rasam Powder", "Spices"), ("Biryani Masala", "Spices"), ("Chaat Masala", "Spices"),
            ("Amchur (Dry Mango Powder)", "Spices"), ("Hing (Asafoetida)", "Spices"), ("Kashmiri Chilli Powder", "Spices"),
            ("Black Pepper Powder", "Spices"), ("Meat Masala", "Spices"), ("Kitchen King Masala", "Spices"),

            # OILS & FATS
            ("Gingelly Oil (Sesame)", "Condiments"), ("Coconut Oil", "Condiments"), ("Groundnut Oil", "Condiments"),
            ("Sunflower Oil", "Condiments"), ("Mustard Oil", "Condiments"), ("Refined Oil", "Condiments"),
            ("Ghee", "Dairy & Eggs"), ("Butter", "Dairy & Eggs"), ("Vanaspati (Dalda)", "Condiments"),

            # DAIRY
            ("Milk", "Dairy & Eggs"), ("Curd (Yoghurt)", "Dairy & Eggs"), ("Buttermilk (Moru)", "Dairy & Eggs"),
            ("Paneer", "Dairy & Eggs"), ("Khoya / Mawa", "Dairy & Eggs"), ("Cream", "Dairy & Eggs"),
            ("Condensed Milk", "Dairy & Eggs"), ("Cheese", "Dairy & Eggs"),

            # NUTS & DRY FRUITS
            ("Cashew", "Pantry"), ("Almonds", "Pantry"), ("Peanuts", "Pantry"), ("Walnuts", "Pantry"),
            ("Pistachios", "Pantry"), ("Raisins", "Pantry"), ("Dried Figs", "Pantry"), ("Dried Apricots", "Pantry"),
            ("Charoli (Chironji)", "Pantry"), ("Melon Seeds (Magaz)", "Pantry"), ("Lotus Seeds (Makhana)", "Pantry"),
            ("Desiccated Coconut", "Pantry"),

            # SWEETENERS
            ("Sugar", "Pantry"), ("Jaggery (Vellam)", "Pantry"), ("Palm Sugar", "Pantry"),
            ("Coconut Sugar", "Pantry"), ("Honey", "Pantry"), ("Nolen Gur", "Pantry"), ("Mishri", "Pantry"),

            # GRAINS & MILLETS
            ("Ragi", "Pantry"), ("Bajra", "Pantry"), ("Jowar", "Pantry"), ("Foxtail Millet", "Pantry"),
            ("Kodo Millet", "Pantry"), ("Little Millet", "Pantry"), ("Barnyard Millet", "Pantry"),
            ("Proso Millet", "Pantry"), ("Oats", "Pantry"), ("Barley", "Pantry"),

            # CONDIMENTS & PASTES
            ("Tamarind Paste", "Condiments"), ("Ginger Garlic Paste", "Condiments"), ("Coconut Milk", "Condiments"),
            ("Green Chilli Paste", "Condiments"), ("Tomato Paste", "Condiments"), ("Vinegar", "Condiments"),
            ("Soy Sauce", "Condiments"),

            # LEAVENING & BINDING
            ("Baking Soda", "Pantry"), ("Baking Powder", "Pantry"), ("Yeast", "Pantry"),

            # EGGS & MEAT
            ("Egg", "Meat"), ("Chicken", "Meat"), ("Mutton / Lamb", "Meat"),
            ("Fish (Rohu, Katla, Pomfret, Seer, Sardine, Tuna)", "Seafood"), ("Prawn", "Seafood"),
            ("Crab", "Seafood"), ("Pork", "Meat"), ("Beef", "Meat")
        ]
        
        # Clean up old duplicate ingredients that are no longer in the master list
        massive_names = {name for name, _ in massive_ingredients}
        to_delete = Ingredient.query.filter(~Ingredient.name.in_(massive_names)).all()
        if to_delete:
            for item in to_delete:
                db.session.delete(item)
            db.session.commit()

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
        # AI Engine returns "name", not "title"
        title = recipe.get("name", "Unknown Recipe")
        
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
