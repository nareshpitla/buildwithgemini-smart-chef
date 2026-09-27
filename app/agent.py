# ruff: noqa
# Copyright 2026 Google LLC

import datetime
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo
from google import genai
from google.cloud import firestore, storage

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from .a2ui_utils import a2ui_callback

MODEL = "gemini-3.8-flash"

# CRITICAL: Hardcode project ID explicitly as a string (NOT project number or env var)
FIRESTORE_PROJECT = "qwiklabs-gcp-03-eaf5ec15fee0"
GCS_BUCKET_NAME = "smart-chef-images-qwiklabs-gcp-03-eaf5ec15fee0"

db = firestore.Client(project=FIRESTORE_PROJECT)
storage_client = storage.Client(project=FIRESTORE_PROJECT)

# Load Agent Engine resource name or sandbox resource name from deployment_metadata.json if available
DEPLOYMENT_METADATA_FILE = Path(__file__).parent.parent / "deployment_metadata.json"
agent_engine_resource_name = None
sandbox_resource_name = None
MEMORY_BANK_ID = "7566816482366062592"

if DEPLOYMENT_METADATA_FILE.exists():
    try:
        with open(DEPLOYMENT_METADATA_FILE) as f:
            metadata = json.load(f)
            agent_engine_resource_name = metadata.get("agent_engine_resource_name")
            sandbox_resource_name = metadata.get("sandbox_resource_name")
            if agent_engine_resource_name:
                MEMORY_BANK_ID = agent_engine_resource_name.split("/")[-1]
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name,
    sandbox_resource_name=sandbox_resource_name,
)


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: after each turn, send the session to Memory Bank for extraction."""
    try:
        if getattr(callback_context, "memory_service", None):
            await callback_context.add_session_to_memory()
    except Exception:
        pass
    return None


def search_recipes(query: str = "", dietary_tag: str = "") -> list[dict]:
    """Search recipes in Firestore by keyword query or dietary tag (e.g. 'vegan', 'gluten-free').

    Args:
        query: Optional search keyword to filter by title or ingredient.
        dietary_tag: Optional dietary tag to filter recipes by (e.g., 'vegan', 'vegetarian', 'gluten-free').

    Returns:
        List of matching recipe dictionaries.
    """
    recipes_ref = db.collection("recipes")
    docs = recipes_ref.stream()
    results = []
    
    q_clean = query.lower().strip()
    tag_clean = dietary_tag.lower().strip()

    for doc in docs:
        data = doc.to_dict()
        title = data.get("title", "").lower()
        ingredients = [i.lower() for i in data.get("ingredients", [])]
        tags = [t.lower() for t in data.get("dietary_tags", [])]

        match_query = not q_clean or (q_clean in title or any(q_clean in ing for ing in ingredients))
        match_tag = not tag_clean or (tag_clean in tags)

        if match_query and match_tag:
            results.append(data)

    return results


def add_recipe(
    title: str,
    cuisine: str,
    ingredients: list[str],
    prep_time_minutes: int,
    instructions: str,
    dietary_tags: list[str] = [],
) -> str:
    """Add a new recipe document to Firestore.

    Args:
        title: Title of the recipe.
        cuisine: Cuisine type (e.g., 'Italian', 'Mexican').
        ingredients: List of ingredient strings.
        prep_time_minutes: Preparation time in minutes.
        instructions: Step-by-step cooking instructions.
        dietary_tags: List of dietary tags (e.g., ['vegan', 'gluten-free']).

    Returns:
        A confirmation message with doc ID.
    """
    doc_id = title.lower().replace(" ", "-")
    doc_data = {
        "id": doc_id,
        "title": title,
        "cuisine": cuisine,
        "ingredients": ingredients,
        "prep_time_minutes": prep_time_minutes,
        "instructions": instructions,
        "dietary_tags": dietary_tags,
    }
    db.collection("recipes").document(doc_id).set(doc_data)
    return f"Successfully added recipe '{title}' to Firestore with ID '{doc_id}'."


def get_pantry_items() -> list[dict]:
    """Get all current items stored in the pantry Firestore collection.

    Returns:
        List of pantry item dictionaries containing item name and quantity.
    """
    pantry_ref = db.collection("pantry")
    docs = pantry_ref.stream()
    items = []
    for doc in docs:
        items.append(doc.to_dict())
    return items


def add_pantry_item(item_name: str, quantity: str) -> str:
    """Add or update an item in the pantry Firestore collection.

    Args:
        item_name: Name of the pantry item (e.g. 'olive oil', 'chickpeas').
        quantity: Quantity string (e.g. '2 cans', '500 ml').

    Returns:
        A confirmation message string.
    """
    doc_id = item_name.lower().replace(" ", "_")
    item_data = {"name": item_name, "quantity": quantity}
    db.collection("pantry").document(doc_id).set(item_data)
    return f"Successfully updated pantry item '{item_name}' with quantity '{quantity}'."


def add_to_grocery_list(items: list[str]) -> str:
    """Add missing items or ingredients to the user's grocery shopping list in Firestore.

    Args:
        items: List of item strings (e.g. ['2 cans chickpeas', '1 bottle olive oil']).

    Returns:
        Confirmation message string.
    """
    grocery_ref = db.collection("grocery_list")
    added = []
    for item in items:
        doc_id = item.lower().replace(" ", "_")[:50]
        grocery_ref.document(doc_id).set({
            "item": item,
            "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "pending"
        })
        added.append(item)
    return f"Successfully added {len(added)} item(s) to your grocery list: {', '.join(added)}."


def get_grocery_list() -> list[dict]:
    """Retrieve all pending items on the user's grocery list from Firestore.

    Returns:
        List of grocery item dictionaries.
    """
    grocery_ref = db.collection("grocery_list")
    docs = grocery_ref.stream()
    items = []
    for doc in docs:
        items.append(doc.to_dict())
    return items


def fetch_external_recipes(query: str) -> list[dict]:
    """Fetch real-world recipes and step-by-step instructions from TheMealDB public API.

    Args:
        query: Recipe or main ingredient search query (e.g. 'chicken', 'pasta', 'curry').

    Returns:
        List of simplified recipe dictionaries containing title, category, cuisine, ingredients, and instructions.
    """
    api_key = os.getenv("THEMEALDB_API_KEY", "1")
    url = f"https://www.themealdb.com/api/json/v1/{api_key}/search.php?s={urllib.parse.quote(query.strip())}"
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmartChef/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            meals = data.get("meals") or []
            results = []
            for meal in meals[:3]:
                ingredients = []
                for i in range(1, 21):
                    ing = meal.get(f"strIngredient{i}")
                    meas = meal.get(f"strMeasure{i}")
                    if ing and ing.strip():
                        ingredients.append(f"{meas.strip()} {ing.strip()}".strip() if meas else ing.strip())

                results.append({
                    "title": meal.get("strMeal"),
                    "category": meal.get("strCategory"),
                    "cuisine": meal.get("strArea"),
                    "instructions": meal.get("strInstructions", "")[:300] + "...",
                    "ingredients": ingredients,
                    "thumbnail": meal.get("strMealThumb"),
                })
            return results
    except Exception as e:
        return [{"error": f"Failed to fetch external recipes: {str(e)}"}]


def geocode_address(address: str) -> dict:
    """Convert an address string into geographic coordinates (latitude and longitude) using Google Geocoding API.

    Args:
        address: The address or city string to geocode (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        Dictionary containing formatted address and location coordinates (latitude and longitude).
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not configured."}

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address.strip())}&key={api_key}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("results", [])
            if not results:
                return {"error": f"No geocoding results found for address: '{address}'"}
            first = results[0]
            loc = first.get("geometry", {}).get("location", {})
            return {
                "address": first.get("formatted_address"),
                "location": {
                    "latitude": loc.get("lat"),
                    "longitude": loc.get("lng"),
                },
            }
    except Exception as e:
        return {"error": f"Geocoding API call failed: {str(e)}"}


def find_nearby_places(latitude: float, longitude: float, place_type: str = "grocery_store", radius_meters: float = 3000.0) -> list[dict]:
    """Find nearby places (such as grocery stores or supermarkets) using the Google Places API (New).

    Args:
        latitude: Latitude of the center location.
        longitude: Longitude of the center location.
        place_type: Type of place to search for (e.g. 'grocery_store', 'supermarket', 'bakery').
        radius_meters: Radius around the location in meters (default 3000 meters).

    Returns:
        List of simplified place dictionaries containing name, address, and location coordinates.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY environment variable is not configured."}]

    url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = {
        "includedTypes": [place_type],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": float(radius_meters),
            }
        },
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            places = data.get("places", [])
            results = []
            for place in places:
                display_name = place.get("displayName", {}).get("text", "")
                results.append({
                    "name": display_name,
                    "address": place.get("formattedAddress"),
                    "location": place.get("location"),
                })
            return results
    except Exception as e:
        return [{"error": f"Places API (New) call failed: {str(e)}"}]


def generate_dish_image(dish_name: str, visual_description: str = "", tool_context: ToolContext = None) -> str:
    """Generate a visual presentation preview image for a culinary dish using gemini-3.1-flash-lite-image in global region.

    Saves the image artifact to the Playground session and uploads the bytes to the public Cloud Storage bucket.

    Args:
        dish_name: Name of the food dish or recipe (e.g., 'Avocado Toast', 'Chana Masala').
        visual_description: Optional additional description for visual details.
        tool_context: ADK ToolContext used to record the artifact in Playground.

    Returns:
        Public GCS HTTPS URL of the generated image.
    """
    prompt = f"Professional food photography of {dish_name}. {visual_description}".strip()
    
    genai_client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")
    
    try:
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
        
        img_bytes = None
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if part.inline_data:
                    img_bytes = part.inline_data.data
                    break
            if img_bytes:
                break

        if not img_bytes:
            return "Error: No image content generated from gemini-3.1-flash-lite-image model."

        filename = f"{dish_name.lower().replace(' ', '_')[:30]}_{int(datetime.datetime.now().timestamp())}.jpg"

        # 1. Save as artifact in Playground's Artifacts panel if tool_context is present
        if tool_context:
            artifact_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload image bytes directly to GCS bucket (without writing to a local file)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(f"dishes/{filename}")
        blob.upload_from_string(img_bytes, content_type="image/jpeg")

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/dishes/{filename}"
        return f"Successfully generated image for '{dish_name}'. Public URL: {public_url}"

    except Exception as e:
        return f"Failed to generate dish image: {str(e)}"


def generate_dish_video(dish_name: str, visual_description: str = "", tool_context: ToolContext = None) -> str:
    """Generate a short culinary presentation video preview for a dish using gemini-omni-flash-preview in global region.

    Saves the video artifact to the Playground session and uploads the video bytes directly to the public Cloud Storage bucket.

    Args:
        dish_name: Name of the culinary dish or recipe (e.g., 'Chana Masala', 'Avocado Toast').
        visual_description: Optional description of the cooking action or visual details.
        tool_context: ADK ToolContext used to save the artifact in Playground.

    Returns:
        Public GCS HTTPS URL of the generated video.
    """
    prompt = f"Short high quality culinary video preview of {dish_name}. {visual_description}".strip()
    
    genai_client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location="global")
    
    try:
        response = genai_client.models.generate_content(
            model="gemini-omni-flash-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["VIDEO"],
            ),
        )
        
        video_bytes = None
        mime_type = "video/mp4"
        if response and getattr(response, "candidates", None):
            for candidate in response.candidates:
                if getattr(candidate, "content", None) and getattr(candidate.content, "parts", None):
                    for part in candidate.content.parts:
                        if getattr(part, "inline_data", None):
                            video_bytes = part.inline_data.data
                            if getattr(part.inline_data, "mime_type", None):
                                mime_type = part.inline_data.mime_type
                            break
                if video_bytes:
                    break

        if not video_bytes:
            return "Error: No video content generated from gemini-omni-flash-preview model."

        ext = "mp4" if "mp4" in mime_type else ("webm" if "webm" in mime_type else "mp4")
        filename = f"{dish_name.lower().replace(' ', '_')[:30]}_{int(datetime.datetime.now().timestamp())}.{ext}"

        # 1. Save as artifact in Playground's Artifacts panel if tool_context is present
        if tool_context:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload video bytes directly to GCS bucket (without writing to a local file)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(f"videos/{filename}")
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/videos/{filename}"
        return f"Successfully generated video for '{dish_name}'. Public URL: {public_url}"

    except Exception as e:
        return f"Failed to generate dish video: {str(e)}"


def get_weather(query: str) -> str:
    """Simulates a web search for weather information.

    Args:
        query: Location query.

    Returns:
        Weather information string.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting current time for a location.

    Args:
        query: City name query.

    Returns:
        Current time information string.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


def memory_service_builder():
    """Build Memory Bank service for deployed container / Agent Runtime."""
    return VertexAiMemoryBankService(
        project=FIRESTORE_PROJECT,
        location="us-central1",
        agent_engine_id=MEMORY_BANK_ID,
    )


# Construct A2UI System Prompt (v0.8 with BasicCatalog)
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are Smart Chef, a culinary AI assistant. You help users plan meals, "
        "search for recipes in their local Firestore database or live via TheMealDB API, "
        "manage their pantry stock, build their grocery shopping list, locate nearby grocery stores or markets "
        "using Google Geocoding and Places APIs, and generate dish presentation previews using Gemini image generation.\n\n"
        "CRITICAL MEMORY & ALLERGY SAFETY RULES:\n"
        "1. Active Memory Recall: You remember all user dietary preferences, food allergies, and health restrictions (e.g. peanuts, gluten, dairy, shellfish, tree nuts, eggs, soy) across sessions.\n"
        "2. Strict Allergen Filtering: Whenever the user mentions a new allergy or dietary restriction, acknowledge it immediately so it is recorded into Memory Bank.\n"
        "3. Recipe Safety: NEVER recommend or suggest any recipe or ingredient that contains any of the user's remembered allergens or restricted foods.\n"
        "4. Always verify recipes against remembered user allergies before presenting options."
    ),
    workflow_description="Analyze the request, call function tools, preloaded memory, or code execution whenever requested, and return structured A2UI cards when presenting recipes, pantry items, grocery lists, or places.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="smart_chef",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        search_recipes,
        add_recipe,
        get_pantry_items,
        add_pantry_item,
        add_to_grocery_list,
        get_grocery_list,
        fetch_external_recipes,
        geocode_address,
        find_nearby_places,
        generate_dish_image,
        generate_dish_video,
        get_weather,
        get_current_time,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
