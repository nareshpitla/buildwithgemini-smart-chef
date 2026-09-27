# Smart Chef 🍳

Smart Chef is an AI-powered culinary concierge and meal planning assistant built using the **Google Agent Development Kit (ADK)**, **Vertex AI**, **Firestore**, **Cloud Storage**, and **Google Maps Platform**. It provides personalized recipe discovery, allergen-safe meal recommendations, pantry and grocery tracking, nearby store lookup, and AI-generated visual food previews rendered as structured **A2UI** interface cards.

![Smart Chef Demo](./demo.gif)

---

## Key Features & Capabilities

* **🧠 Active Allergen & Memory Recall**: Uses **Vertex AI Memory Bank** to automatically remember dietary restrictions, food allergies, and preferences across user sessions, ensuring allergen safety.
* **🥫 Pantry & Grocery Management**: Interfaces directly with **Google Cloud Firestore** to track available pantry stock, save custom recipes, and maintain shopping lists.
* **🌐 External Recipe Search**: Queries both local Firestore collections and live external culinary APIs (TheMealDB) for recipe ideas.
* **📍 Nearby Grocer Lookup**: Uses **Google Maps Geocoding** and **Places API (New)** to convert addresses and find nearby grocery stores and specialty food markets.
* **🖼️ AI Image & Video Preview Generation**: Uses `gemini-3.1-flash-lite-image` and `gemini-omni-flash-preview` on Vertex AI to generate food presentation images and short videos, uploading assets directly to **Google Cloud Storage (GCS)**.
* **📱 Structured A2UI Cards**: Renders response surfaces using the A2UI v0.8 schema over the **Agent-to-Agent (A2A)** protocol, formatting components (Card, Column, Row, Text, Image) for frontends.

---

## Google Cloud Services & Models Integrated

| Component | Technology / Service | Role in Application |
| --- | --- | --- |
| **Agent Framework** | Google ADK (`google-adk`) | Agent orchestration, tool integration, and lifecycle callbacks |
| **Core AI Model** | Gemini 2.5 Flash | LLM reasoning engine for meal planning and natural dialogue |
| **Memory Bank** | Vertex AI Memory Bank | Cross-session persistence for user dietary preferences & allergies |
| **Structured Database** | Google Cloud Firestore | NoSQL storage for pantry inventory, saved recipes, and shopping lists |
| **Object Storage** | Google Cloud Storage (GCS) | Storing and serving generated dish images and video preview files |
| **Image Generation** | `gemini-3.1-flash-lite-image` | High-quality dish photography preview generation |
| **Video Generation** | `gemini-omni-flash-preview` | Short culinary video preview synthesis |
| **Location Services** | Google Maps Geocoding & Places API | Geolocation resolution and nearby store discovery |
| **UI Protocol** | A2UI (v0.8 BasicCatalog) | Declarative UI card formatting over A2A protocol |

---

## Project Structure

```
smart-chef/
├── app/
│   └── agent.py              # Root agent, tools, memory callback, A2UI schemas
├── frontend/
│   ├── main.py               # FastAPI proxy server connecting web UI to agent
│   ├── Dockerfile            # Container build specification for Cloud Run deployment
│   └── static/
│       └── index.html        # Interactive chat interface with dark mode & filter chips
├── agents-cli-manifest.yaml  # Deployment manifest and framework metadata
├── demo.gif                  # Inline looping screen recording demo
└── README.md                 # Project documentation
```

---

## Setup & Local Run Instructions

### Prerequisites

* Python 3.11+
* Google Cloud SDK (`gcloud`) authenticated with a GCP project
* `agents-cli` installed (`pip install google-agents-cli`)
* Google Maps API Key set as an environment variable (`GOOGLE_MAPS_API_KEY`)

### 1. Install Dependencies

```bash
# Install backend agent dependencies
pip install google-adk google-genai google-cloud-firestore google-cloud-storage

# Install frontend dependencies
cd frontend
pip install -r requirements.txt
cd ..
```

### 2. Set Up Environment Variables

```bash
export GOOGLE_CLOUD_PROJECT="<YOUR_GCP_PROJECT_ID>"
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_MAPS_API_KEY="<YOUR_GOOGLE_MAPS_API_KEY>"
export AGENT_DIRECTORY="app"
```

### 3. Run the Backend Agent Locally

```bash
agents-cli run --mode a2a "Hello Smart Chef"
```

### 4. Run the Web Frontend Locally

```bash
cd frontend
uvicorn main:app --host 0.0.0.0 --port 8080
```

Once started, open a browser to `http://localhost:8080` to interact with the Smart Chef interface.
