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
import hashlib
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
            ("Onion / Vengayam", "Vegetables"), ("Tomato / Thakkali", "Vegetables"), ("Potato / Urulai Kizhangu", "Vegetables"),
            ("Brinjal / Kathirikai", "Vegetables"), ("Drumstick (Murungakkai)", "Vegetables"),
            ("Raw Banana / Vazhakkai", "Vegetables"), ("Plantain Stem / Vazhaithandu", "Vegetables"), ("Plantain Flower / Vazhaipoo", "Vegetables"),
            ("Bitter Gourd / Pavakkai", "Vegetables"), ("Snake Gourd / Pudalangai", "Vegetables"), ("Ridge Gourd / Peerkangai", "Vegetables"),
            ("Bottle Gourd (Lauki)", "Vegetables"), ("Ash Gourd", "Vegetables"), ("Ivy Gourd (Kovakkai)", "Vegetables"),
            ("Raw Jackfruit / Pala Musu", "Vegetables"), ("Yam (Senai Kizhangu)", "Vegetables"), ("Elephant Foot Yam", "Vegetables"),
            ("Colocasia / Seppankizhangu", "Vegetables"), ("Sweet Potato / Sakkaravalli Kizhangu", "Vegetables"), ("Raw Mango / Mangai", "Vegetables"),
            ("Raw Papaya", "Vegetables"), ("Carrot", "Vegetables"), ("Beans (French Beans)", "Vegetables"),
            ("Cluster Beans", "Vegetables"), ("Broad Beans", "Vegetables"), ("Capsicum", "Vegetables"),
            ("Cauliflower", "Vegetables"), ("Cabbage / Muttaikose", "Vegetables"), ("Broccoli", "Vegetables"),
            ("Spinach / Palak Keerai", "Vegetables"), ("Fenugreek Leaves (Methi)", "Vegetables"),
            ("Drumstick Leaves / Murungai Keerai", "Vegetables"), ("Amaranth Leaves", "Vegetables"), ("Curry Leaves / Kariveppilai", "Vegetables"),
            ("Coriander Leaves / Kothamalli", "Vegetables"), ("Mint Leaves / Pudina", "Vegetables"), ("Spring Onion", "Vegetables"),
            ("Leek", "Vegetables"), ("Radish (Mullangi)", "Vegetables"), ("Turnip", "Vegetables"),
            ("Beetroot", "Vegetables"), ("Pumpkin / Poosanikai", "Vegetables"), ("Corn / Maize", "Vegetables"),
            ("Peas / Pattani", "Vegetables"), ("Lady's Finger / Vendakkai", "Vegetables"), ("Tindora", "Vegetables"),
            ("Raw Turmeric", "Vegetables"), ("Garlic / Poondu", "Vegetables"), ("Ginger / Inji", "Vegetables"),
            ("Green Chilli / Pachai Milagai", "Vegetables"), ("Shallots / Chinna Vengayam", "Vegetables"),

            # FRUITS
            ("Mango / Mambazham", "Fruits"), ("Banana / Vazhaipazham", "Fruits"), ("Coconut / Thengai", "Fruits"), ("Tamarind / Puli", "Fruits"),
            ("Lemon / Elumichai", "Fruits"), ("Lime", "Fruits"), ("Amla / Nellikai", "Fruits"), ("Guava / Koyyapazham", "Fruits"),
            ("Papaya / Pappali", "Fruits"), ("Pineapple", "Fruits"), ("Jackfruit / Palappazham", "Fruits"), ("Watermelon", "Fruits"),
            ("Pomegranate / Madhulai", "Fruits"), ("Dates / Perichambazham", "Fruits"), ("Kokum", "Fruits"), ("Bael Fruit", "Fruits"),
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
            ("Salt", "Spices"), ("Black Salt (Kala Namak)", "Spices"),

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
            ("Crab", "Seafood"), ("Pork", "Meat"), ("Beef", "Meat"),

            # MODERN & RESTAURANT-STYLE VEGETABLES
            ("Baby Corn", "Vegetables"), ("Sweet Corn", "Vegetables"), ("Broccoli", "Vegetables"),
            ("Zucchini", "Vegetables"), ("Celery", "Vegetables"), ("Lettuce", "Vegetables"),
            ("Iceberg Lettuce", "Vegetables"), ("Cherry Tomato", "Vegetables"), ("Sun Dried Tomato", "Vegetables"),
            ("Bell Pepper", "Vegetables"), ("Asparagus", "Vegetables"), ("Avocado", "Vegetables"),
            ("Artichoke", "Vegetables"), ("Leek", "Vegetables"), ("Bok Choy", "Vegetables"),
            ("Purple Cabbage", "Vegetables"), ("Baby Spinach", "Vegetables"), ("Arugula", "Vegetables"),
            ("Mushroom", "Vegetables"), ("Olives", "Vegetables"), ("Jalapeno", "Vegetables"), ("Habanero Chilli", "Vegetables"),

            # NOODLES & PASTA
            ("Hakka Noodles", "Pantry"), ("Rice Noodles", "Pantry"), ("Vermicelli", "Pantry"),
            ("Spaghetti", "Pantry"), ("Penne", "Pantry"), ("Macaroni", "Pantry"), ("Fusilli", "Pantry"),
            ("Lasagne Sheets", "Pantry"), ("Ramen Noodles", "Pantry"), ("Glass Noodles", "Pantry"), ("Udon Noodles", "Pantry"),

            # SAUCES & CONDIMENTS (Modern)
            ("Soy Sauce", "Condiments"), ("Oyster Sauce", "Condiments"), ("Fish Sauce", "Condiments"),
            ("Schezwan Sauce", "Condiments"), ("Hoisin Sauce", "Condiments"), ("Sriracha Sauce", "Condiments"),
            ("Tabasco Sauce", "Condiments"), ("Worcestershire Sauce", "Condiments"), ("Tomato Ketchup", "Condiments"),
            ("Mayonnaise", "Condiments"), ("Mustard Sauce", "Condiments"), ("Barbecue Sauce", "Condiments"),
            ("Hot Sauce", "Condiments"), ("Teriyaki Sauce", "Condiments"), ("Sweet Chilli Sauce", "Condiments"),
            ("Pasta Sauce", "Condiments"), ("Pesto Sauce", "Condiments"), ("Hummus", "Condiments"), ("Tzatziki", "Condiments"),

            # CHEESE VARIETIES
            ("Mozzarella", "Dairy & Eggs"), ("Cheddar", "Dairy & Eggs"), ("Parmesan", "Dairy & Eggs"),
            ("Feta", "Dairy & Eggs"), ("Cream Cheese", "Dairy & Eggs"), ("Ricotta", "Dairy & Eggs"),
            ("Gouda", "Dairy & Eggs"), ("Processed Cheese Slices", "Dairy & Eggs"), ("Cheese Spread", "Dairy & Eggs"),
            ("Bocconcini", "Dairy & Eggs"),

            # DAIRY & ALTERNATIVES (Modern)
            ("Whipping Cream", "Dairy & Eggs"), ("Heavy Cream", "Dairy & Eggs"), ("Sour Cream", "Dairy & Eggs"),
            ("Crème Fraîche", "Dairy & Eggs"), ("Greek Yoghurt", "Dairy & Eggs"), ("Almond Milk", "Dairy & Eggs"),
            ("Oat Milk", "Dairy & Eggs"), ("Coconut Milk (Canned)", "Dairy & Eggs"), ("Coconut Cream", "Dairy & Eggs"),
            ("Evaporated Milk", "Dairy & Eggs"),

            # HERBS (Fresh & Dried)
            ("Basil", "Herbs"), ("Oregano", "Herbs"), ("Thyme", "Herbs"), ("Rosemary", "Herbs"),
            ("Parsley", "Herbs"), ("Chives", "Herbs"), ("Dill", "Herbs"), ("Tarragon", "Herbs"),
            ("Sage", "Herbs"), ("Bay Leaves", "Herbs"), ("Lemongrass", "Herbs"), ("Kaffir Lime Leaves", "Herbs"),

            # BAKING INGREDIENTS
            ("All Purpose Flour (Maida)", "Pantry"), ("Bread Flour", "Pantry"), ("Almond Flour", "Pantry"),
            ("Cocoa Powder", "Pantry"), ("Dark Chocolate", "Pantry"), ("Milk Chocolate", "Pantry"),
            ("White Chocolate", "Pantry"), ("Chocolate Chips", "Pantry"), ("Vanilla Extract", "Pantry"),
            ("Vanilla Essence", "Pantry"), ("Baking Soda", "Pantry"), ("Baking Powder", "Pantry"),
            ("Dry Yeast", "Pantry"), ("Instant Yeast", "Pantry"), ("Gelatin", "Pantry"), ("Agar Agar", "Pantry"),
            ("Cornstarch", "Pantry"), ("Arrowroot Powder", "Pantry"), ("Cream of Tartar", "Pantry"),
            ("Food Colouring", "Pantry"), ("Edible Glitter", "Pantry"), ("Sprinkles", "Pantry"),
            ("Icing Sugar", "Pantry"), ("Brown Sugar", "Pantry"), ("Demerara Sugar", "Pantry"), ("Caster Sugar", "Pantry"),

            # OILS (Modern)
            ("Olive Oil", "Condiments"), ("Extra Virgin Olive Oil", "Condiments"), ("Avocado Oil", "Condiments"),
            ("Canola Oil", "Condiments"), ("Rice Bran Oil", "Condiments"), ("Flaxseed Oil", "Condiments"),
            ("Truffle Oil", "Condiments"), ("Sesame Oil (Toasted)", "Condiments"),

            # VINEGARS
            ("Apple Cider Vinegar", "Condiments"), ("White Vinegar", "Condiments"), ("Balsamic Vinegar", "Condiments"),
            ("Red Wine Vinegar", "Condiments"), ("Rice Wine Vinegar", "Condiments"),

            # SPREADS & BUTTERS
            ("Peanut Butter", "Condiments"), ("Almond Butter", "Condiments"), ("Nutella", "Condiments"),
            ("Tahini", "Condiments"), ("Jam / Fruit Preserves", "Condiments"), ("Marmalade", "Condiments"),
            ("Salted Butter", "Dairy & Eggs"), ("Unsalted Butter", "Dairy & Eggs"),

            # BREADS & WRAPS
            ("White Bread", "Pantry"), ("Brown Bread", "Pantry"), ("Multigrain Bread", "Pantry"),
            ("Sourdough Bread", "Pantry"), ("Pita Bread", "Pantry"), ("Tortilla Wrap", "Pantry"),
            ("Burger Buns", "Pantry"), ("Hot Dog Buns", "Pantry"), ("Focaccia", "Pantry"),
            ("Ciabatta", "Pantry"), ("Bagel", "Pantry"), ("Croissant", "Pantry"),

            # CANNED & PACKAGED
            ("Canned Tomatoes", "Pantry"), ("Canned Chickpeas", "Pantry"), ("Canned Kidney Beans", "Pantry"),
            ("Canned Corn", "Pantry"), ("Canned Tuna", "Pantry"), ("Tomato Puree (Packaged)", "Pantry"),
            ("Vegetable / Chicken Stock", "Pantry"), ("Stock Cubes", "Pantry"),

            # PROTEINS (Modern)
            ("Tofu", "Dairy & Eggs"), ("Tempeh", "Dairy & Eggs"), ("Soya Chunks", "Dairy & Eggs"),
            ("TVP", "Pantry"), ("Paneer", "Dairy & Eggs"), ("Seitan", "Meat"),
            ("Edamame", "Vegetables"), ("Smoked Salmon", "Seafood"), ("Salami", "Meat"), ("Pepperoni", "Meat"),

            # GRAINS (International)
            ("Quinoa", "Pantry"), ("Couscous", "Pantry"), ("Bulgur Wheat", "Pantry"),
            ("Freekeh", "Pantry"), ("Farro", "Pantry"), ("Polenta", "Pantry"), ("Arborio Rice", "Pantry"),

            # SOUTH INDIAN & TAMIL SPECIFIC
            ("Keerai (Purslane)", "Vegetables"), ("Ponnanganni Keerai", "Vegetables"), ("Manathakkali Keerai", "Vegetables"),
            ("Agathi Keerai", "Vegetables"), ("Mudakathan Keerai", "Vegetables"), ("Sirukeerai", "Vegetables"),
            ("Siru Paruppu", "Pantry"), ("Mochai (Field Beans)", "Pantry"), ("Sundakkai (Turkey Berry)", "Vegetables"),
            ("Manathakkali Vathal", "Pantry"), ("Sundakkai Vathal", "Pantry"), ("Vengaya Thol", "Pantry"),
            ("Neem Flower (Veppam Poo)", "Spices"), ("Banana Leaf", "Pantry"), ("Lotus Root", "Vegetables"),
            ("Taro Stem", "Vegetables"), ("Raw Coconut Flower", "Vegetables"), ("Jackfruit Seeds", "Pantry"),
            ("Mango Kernel", "Pantry"), ("Breadfruit", "Vegetables"), ("Nendran Banana", "Fruits"),
            ("Red Banana", "Fruits"), ("Poovan Banana", "Fruits"), ("Karpooravalli", "Herbs"),
            ("Tulsi (Holy Basil)", "Herbs"), ("Pandan Leaf", "Herbs"),

            # TAMIL NADU SPICES & MASALAS
            ("Kandathippili", "Spices"), ("Omavalli (Ajwain Leaf)", "Herbs"), ("Kadalpasi (Seaweed)", "Spices"),
            ("Nati Milagu", "Spices"), ("Pul Milagai", "Vegetables"), ("Gundu Milagai", "Spices"),
            ("Kolumbu Podi", "Spices"), ("Vatha Kuzhambu Podi", "Spices"), ("Kootu Podi", "Spices"),
            ("Idli Milagai Podi", "Spices"), ("Paruppu Podi", "Spices"), ("Curry Masala Powder", "Spices"),
            ("Chettinad Masala Powder", "Spices"),

            # KERALA & ANDHRA SPECIFIC
            ("Kudampuli", "Spices"), ("Coconut Vinegar", "Condiments"), ("Thalippu Vengayam", "Vegetables"),
            ("Nadan Kozhi", "Meat"), ("Koorka", "Vegetables"), ("Vathal", "Pantry"),
            ("Gongura", "Vegetables"), ("Chepalu", "Seafood"), ("Avakai", "Condiments"), ("Dosakaya", "Vegetables"),

            # NORTH & WEST INDIAN SPECIFIC
            ("Sarson (Mustard Greens)", "Vegetables"), ("Bathua", "Vegetables"), ("Tinda", "Vegetables"),
            ("Parwal", "Vegetables"), ("Singhara", "Vegetables"), ("Kamal Kakdi", "Vegetables"),
            ("Betel Leaf", "Herbs"), ("Dried Pomegranate Seeds", "Spices"), ("Sattu", "Pantry"),
            ("Mishti Doi", "Dairy & Eggs"), ("Tirphal", "Spices"), ("Tamdi Bhaji", "Vegetables"),
            ("Suva Bhaji", "Vegetables"), ("Vatana", "Pantry"), ("Dalimbi", "Pantry"),
            ("Sol Kadhi base", "Condiments"), ("Amsul", "Spices"), ("Vindaloo Masala", "Spices"),
            ("Recheado Masala", "Spices"),

            # EAST INDIAN & RAJASTHANI SPECIFIC
            ("Shorshe (Mustard Paste)", "Condiments"), ("Radhuni", "Spices"), ("Panch Phoron", "Spices"),
            ("Hilsa Fish", "Seafood"), ("Bori", "Pantry"), ("Potol", "Vegetables"), ("Gondhoraj Lebu", "Fruits"),
            ("Ker", "Pantry"), ("Sangri", "Pantry"), ("Ker Sangri", "Pantry"), ("Surti Papdi", "Vegetables"),
            ("Valor", "Vegetables"), ("Kand", "Vegetables"), ("Khatta Dhokla base", "Pantry"),

            # NORTHEAST INDIA SPECIFIC
            ("Bhut Jolokia", "Vegetables"), ("Naga Chilli", "Vegetables"), ("Bamboo Shoot", "Vegetables"),
            ("Axone", "Condiments"), ("Kingfish", "Seafood"), ("Smoked Pork", "Meat"), ("Dried Fish (Shidal)", "Seafood"),
            ("Black Sesame", "Spices"), ("Perilla Seeds", "Spices"), ("Taro Leaves", "Vegetables"),
            ("Wild Mushroom", "Vegetables"), ("Rice Beer", "Condiments"), ("Lakadong Turmeric", "Spices"),

            # INTERNATIONAL MISSING
            ("Miso Paste", "Condiments"), ("Gochujang", "Condiments"), ("Harissa Paste", "Condiments"),
            ("Sambal Oelek", "Condiments"), ("Doubanjiang", "Condiments"), ("Shaoxing Rice Wine", "Condiments"),
            ("Mirin", "Condiments"), ("Sake", "Condiments"), ("Dashi Stock", "Pantry"), ("Nori", "Pantry"),
            ("Wakame Seaweed", "Pantry"), ("Kombu", "Pantry"), ("Bonito Flakes", "Pantry"), ("Chickpea Brine", "Pantry"),
            ("Nutritional Yeast", "Pantry"), ("Liquid Smoke", "Condiments"), ("Capers", "Condiments"),
            ("Anchovies", "Seafood"), ("Sun Dried Olives", "Pantry"), ("Preserved Lemon", "Condiments"),
            ("Za'atar", "Spices"), ("Sumac", "Spices"), ("Baharat Spice Mix", "Spices"), ("Ras el Hanout", "Spices"),
            ("Smoked Paprika", "Spices"), ("Sweet Paprika", "Spices"), ("Chipotle Pepper", "Spices"),
            ("Ancho Chilli", "Spices"), ("Guajillo Chilli", "Spices"), ("Epazote", "Herbs"),

            # MISSING SEAFOOD
            ("Mackerel", "Seafood"), ("Sardine", "Seafood"), ("Tilapia", "Seafood"), ("Catfish", "Seafood"),
            ("Squid / Calamari", "Seafood"), ("Lobster", "Seafood"), ("Oyster", "Seafood"), ("Mussel", "Seafood"),
            ("Clam", "Seafood"), ("Dried Shrimp", "Seafood"), ("Bombay Duck", "Seafood"), ("Rawas", "Seafood"),
            ("Bangda", "Seafood"),

            # MISSING FRUITS
            ("Custard Apple", "Fruits"), ("Sapota (Chikoo)", "Fruits"), ("Fig (Fresh)", "Fruits"), ("Mulberry", "Fruits"),
            ("Dragon Fruit", "Fruits"), ("Passion Fruit", "Fruits"), ("Kiwi", "Fruits"), ("Strawberry", "Fruits"),
            ("Blueberry", "Fruits"), ("Raspberry", "Fruits"), ("Cranberry", "Fruits"), ("Peach", "Fruits"),
            ("Plum", "Fruits"), ("Apricot (Fresh)", "Fruits"), ("Grape", "Fruits"), ("Orange", "Fruits"),
            ("Sweet Lime (Mosambi)", "Fruits"), ("Grapefruit", "Fruits"), ("Tangerine", "Fruits"),
            ("Pear", "Fruits"), ("Apple", "Fruits"), ("Gooseberry", "Fruits"),

            # MUSHROOMS
            ("Button Mushroom", "Vegetables"), ("Oyster Mushroom", "Vegetables"), ("Shiitake Mushroom", "Vegetables"),
            ("Portobello Mushroom", "Vegetables"), ("King Oyster Mushroom", "Vegetables"), ("Straw Mushroom", "Vegetables"),
            ("Milky Mushroom", "Vegetables"), ("Paddy Straw Mushroom", "Vegetables"), ("Dhingri Mushroom", "Vegetables")
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
        raw_key = "|".join(sorted(ingredients)).lower()
        cache_key = hashlib.md5(raw_key.encode()).hexdigest()
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
