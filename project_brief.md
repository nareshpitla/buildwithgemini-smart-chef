# My agent: Smart Chef & Recipe Concierge (smart-chef)

One-liner: A conversational agent that helps home cooks plan meals, search recipes grounded in a real culinary database, track pantry ingredients, and generate dish presentation previews.

## Tool Coverage
- **Memory**: Remembers user dietary restrictions (e.g., vegan, gluten-free), ingredient allergies, pantry inventory, and favorite cuisines across sessions.
- **Tools**: `search_recipes` (looks up recipes by ingredient/cuisine), `check_pantry` (queries pantry stock), and `add_to_grocery_list` (saves missing ingredients).
- **Catalog / UI**: Recipe cards and structured ingredient lists rendered using A2UI cards.
- **Image Gen**: Generates visual presentation previews of finished plated dishes on demand.
- **Sandbox**: Computes ingredient scaling ratios for different serving sizes and calculates total nutritional macros (calories, protein, carbs, fat).

## Workshop Tool Integration
- **Sessions & Memory**: Vertex AI Memory Bank / Agent Platform Sessions
- **Structured Data**: Firestore database for recipe catalog and pantry stock
- **Agent Framework**: ADK (Agent Development Kit) with Python function tools
- **Agent UI**: A2UI cards for recipes & meal plans
