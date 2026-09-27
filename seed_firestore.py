# Copyright 2026 Google LLC
# Seed script for Firestore recipes & pantry collections

from google.cloud import firestore

# CRITICAL: Hardcode project ID explicitly as a string (NOT project number or env var)
FIRESTORE_PROJECT = "qwiklabs-gcp-03-eaf5ec15fee0"

db = firestore.Client(project=FIRESTORE_PROJECT)

SAMPLE_RECIPES = [
    {
        "id": "avocado-toast",
        "title": "Avocado & Tomato Toast",
        "cuisine": "American",
        "ingredients": ["bread", "avocado", "cherry tomatoes", "olive oil", "salt", "pepper"],
        "prep_time_minutes": 10,
        "instructions": "Toast the bread. Mash avocado with olive oil, salt, and pepper. Spread on toast and top with sliced cherry tomatoes.",
        "dietary_tags": ["vegan", "vegetarian", "dairy-free"],
    },
    {
        "id": "quinoa-salad",
        "title": "Mediterranean Quinoa Bowl",
        "cuisine": "Mediterranean",
        "ingredients": ["quinoa", "cucumber", "cherry tomatoes", "kalamata olives", "feta cheese", "lemon juice"],
        "prep_time_minutes": 20,
        "instructions": "Cook quinoa. Toss with diced cucumber, tomatoes, olives, crumbled feta, and lemon juice dressing.",
        "dietary_tags": ["vegetarian", "gluten-free"],
    },
    {
        "id": "chana-masala",
        "title": "Classic Chana Masala",
        "cuisine": "Indian",
        "ingredients": ["chickpeas", "tomatoes", "onion", "garlic", "ginger", "garam masala", "cumin", "turmeric"],
        "prep_time_minutes": 30,
        "instructions": "Sauté onion, garlic, and ginger. Add spices and tomatoes, then simmer chickpeas for 20 minutes.",
        "dietary_tags": ["vegan", "gluten-free", "dairy-free"],
    },
    {
        "id": "thai-green-curry",
        "title": "Thai Coconut Green Curry",
        "cuisine": "Thai",
        "ingredients": ["coconut milk", "green curry paste", "tofu", "bamboo shoots", "bell pepper", "basil"],
        "prep_time_minutes": 25,
        "instructions": "Heat green curry paste in coconut milk. Add cubed tofu and vegetables, simmer until tender, finish with basil.",
        "dietary_tags": ["vegan", "gluten-free", "dairy-free"],
    },
]

SAMPLE_PANTRY = [
    {"name": "chickpeas", "quantity": "2 cans"},
    {"name": "avocado", "quantity": "3 whole"},
    {"name": "cherry tomatoes", "quantity": "1 pint"},
    {"name": "olive oil", "quantity": "500 ml"},
    {"name": "quinoa", "quantity": "1 lb"},
]


def seed_database():
    print(f"Seeding Firestore in project '{FIRESTORE_PROJECT}'...")
    
    recipes_ref = db.collection("recipes")
    for recipe in SAMPLE_RECIPES:
        doc_id = recipe["id"]
        recipes_ref.document(doc_id).set(recipe)
        print(f"  ✓ Seeded recipe: {recipe['title']} ({doc_id})")
        
    pantry_ref = db.collection("pantry")
    for item in SAMPLE_PANTRY:
        pantry_ref.document(item["name"].replace(" ", "_")).set(item)
        print(f"  ✓ Seeded pantry item: {item['name']}")

    print("Seeding completed successfully! ✅")


if __name__ == "__main__":
    seed_database()
