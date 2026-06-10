"""
Seed the database with a comprehensive master ingredients list for autocomplete.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db, Ingredient

INGREDIENTS = {
    "Vegetables": [
        "Onion", "Tomato", "Potato", "Carrot", "Capsicum", "Spinach",
        "Broccoli", "Cauliflower", "Cabbage", "Green Peas", "Corn",
        "Mushroom", "Zucchini", "Beetroot", "Eggplant", "Cucumber",
        "Lettuce", "Bell Pepper", "Green Beans", "Okra", "Radish",
        "Pumpkin", "Sweet Potato", "Spring Onion", "Celery",
        "Asparagus", "Kale", "Leek", "Turnip", "Artichoke",
    ],
    "Fruits": [
        "Lemon", "Lime", "Orange", "Apple", "Banana", "Mango",
        "Pineapple", "Coconut", "Avocado", "Strawberry", "Blueberry",
        "Grapes", "Watermelon", "Papaya", "Pomegranate", "Tamarind",
    ],
    "Proteins": [
        "Egg", "Chicken", "Paneer", "Fish", "Tofu", "Mutton",
        "Prawns", "Shrimp", "Lamb", "Beef", "Pork", "Turkey",
        "Salmon", "Tuna", "Crab", "Soya Chunks", "Chickpeas",
        "Lentils", "Kidney Beans", "Black Beans", "Green Gram",
    ],
    "Grains & Carbs": [
        "Rice", "Bread", "Pasta", "Noodles", "Wheat Flour", "Maida",
        "Oats", "Quinoa", "Couscous", "Tortilla", "Pita Bread",
        "Semolina", "Rice Flour", "Cornflour", "Breadcrumbs",
        "Puff Pastry", "Pizza Dough",
    ],
    "Dairy": [
        "Milk", "Butter", "Cheese", "Cream", "Yogurt", "Ghee",
        "Sour Cream", "Cream Cheese", "Mozzarella", "Parmesan",
        "Cheddar", "Cottage Cheese", "Condensed Milk", "Whipped Cream",
    ],
    "Spices & Seasonings": [
        "Salt", "Black Pepper", "Turmeric", "Red Chili Powder",
        "Cumin Seeds", "Cumin Powder", "Coriander Powder",
        "Garam Masala", "Mustard Seeds", "Cinnamon", "Cardamom",
        "Cloves", "Bay Leaf", "Oregano", "Basil", "Thyme",
        "Rosemary", "Paprika", "Chili Flakes", "White Pepper",
        "Nutmeg", "Fennel Seeds", "Fenugreek", "Asafoetida",
        "Star Anise", "Saffron", "Mint Leaves", "Curry Leaves",
        "Coriander Leaves",
    ],
    "Sauces & Condiments": [
        "Soy Sauce", "Tomato Ketchup", "Vinegar", "Olive Oil",
        "Sesame Oil", "Mustard Sauce", "Hot Sauce", "Worcestershire Sauce",
        "Oyster Sauce", "Fish Sauce", "Hoisin Sauce", "Sriracha",
        "Barbecue Sauce", "Mayonnaise", "Tahini", "Pesto",
        "Coconut Milk", "Coconut Cream", "Tomato Paste", "Honey",
        "Maple Syrup", "Coconut Aminos",
    ],
    "Oils & Fats": [
        "Vegetable Oil", "Sunflower Oil", "Coconut Oil",
        "Refined Oil", "Mustard Oil", "Peanut Oil",
    ],
    "Nuts & Seeds": [
        "Peanuts", "Cashew", "Almonds", "Walnuts", "Pistachios",
        "Sesame Seeds", "Flax Seeds", "Chia Seeds", "Sunflower Seeds",
        "Pine Nuts", "Poppy Seeds",
    ],
    "Others": [
        "Sugar", "Brown Sugar", "Jaggery", "Garlic", "Ginger",
        "Green Chili", "Baking Powder", "Baking Soda", "Yeast",
        "Cocoa Powder", "Chocolate", "Vanilla Extract", "Food Color",
        "Gelatin", "Agar Agar", "Cornstarch",
    ],
}


def seed_database():
    """Populate the database with the master ingredients list."""
    app = create_app()

    with app.app_context():
        db.create_all()

        # Check if already seeded
        existing = Ingredient.query.count()
        if existing > 0:
            print(f"Database already has {existing} ingredients. Skipping seed.")
            return

        count = 0
        for category, items in INGREDIENTS.items():
            for name in items:
                ingredient = Ingredient(name=name, category=category)
                db.session.add(ingredient)
                count += 1

        db.session.commit()
        print(f"[OK] Seeded {count} ingredients across {len(INGREDIENTS)} categories.")


if __name__ == "__main__":
    seed_database()
