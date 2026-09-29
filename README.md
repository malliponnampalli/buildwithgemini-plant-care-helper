# 🌿 Plant Care Helper

A conversational AI agent built with Google's Agent Development Kit (ADK) that helps plant owners care for their indoor garden with a catalog database, real-time weather integration, botanical lookups, visual media generation, and personalized memory.

![Plant Care Helper Demo](./demo.gif)

---

## 🚀 Implemented Features & Architecture

This project is built on **ADK 1.1.0** and implements the following Google Cloud services, AI models, and APIs:

### 🗄️ Database & Memory Integration
- **Google Cloud Firestore**: Provides persistence for the indoor plant collection, catalog searches (`search_plants_catalog`), plant details lookup (`get_plant_details`), care action logging (`log_plant_care`), and adding or updating plant profiles (`add_or_update_plant`).
- **Vertex AI Memory Bank**: Integrates cross-session long-term memory using `PreloadMemoryTool` and `generate_memories_callback`. Automatically extracts and persists user care preferences, light levels, household pet safety constraints, and plant/pollen allergies.

### 🎨 Visual & Multimodal Media Generation
- **Imagen 3 (`gemini-3.1-flash-lite-image`)**: Custom image generation tool (`generate_plant_image`) operating in the `global` region. Generates high-quality photos of plant decor setups and care concepts, saves session artifacts via `tool_context.save_artifact`, and uploads media directly to a public Google Cloud Storage bucket.
- **Google Omni Model (`gemini-omni-flash-preview`)**: Short video generation tool (`generate_plant_video`) in the `global` region. Creates plant growth timelapses and care video tutorials, saving video artifacts and uploading `.mp4` media directly to Cloud Storage.
- **Google Cloud Storage**: Public media storage bucket hosting generated plant images and videos with public HTTPS URLs.

### 🖼️ Agent UI (A2UI v0.8)
- **A2UI Basic Catalog**: Integrated via `A2uiSchemaManager` (version 0.8) and `a2ui_callback`. Automatically renders agent responses as rich cards, columns, text nodes, and image displays both in ADK Web and in the custom web frontend.

### 🌐 External Tool & API Integrations
- **Open-Meteo Weather API**: Fetches real-time temperature and relative humidity (`get_local_weather_and_humidity`) to dynamically adjust plant watering recommendations.
- **iNaturalist Botanical API**: Looks up official scientific taxonomy, common names, Wikipedia references, and sample photography (`lookup_botanical_info`).
- **Google Maps Geocoding API**: Converts street addresses or place names into geographical coordinates (`geocode_address`).
- **Google Places API (New)**: Searches nearby plant nurseries, florists, and home garden stores (`find_nearby_places`).
- **Python Code Execution Sandbox**: Calculates soil drying rates and exact watering volumes based on pot diameter and ambient temperature.

---

## 🛠️ Local Setup & Execution

### Prerequisites
- Python 3.10+
- Node.js & `uv` package manager
- Google Cloud Project with Vertex AI, Firestore, and Cloud Storage APIs enabled

### 1. Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
pip install -r requirements.txt
cd ..
```

### 2. Run Local ADK Playground
To launch the agent playground with Vertex AI Memory Bank enabled:
```bash
uv run adk web . --port 8080 --reload_agents --memory_service_uri=agentengine://<YOUR_AGENT_ENGINE_ID>
```

### 3. Run Custom Chat Frontend Locally
To start the FastAPI A2A proxy and lightweight chat UI:
```bash
cd frontend
export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_NUMBER>/locations/us-central1/reasoningEngines/<RESOURCE_ID>"
export AGENT_DIRECTORY="app"
python main.py
```

### 4. Deploy Frontend to Cloud Run
To deploy the custom chat frontend to Google Cloud Run:
```bash
gcloud run deploy plant-care-helper-frontend \
  --source=/path/to/plant-care-helper/frontend \
  --region=us-east1 \
  --set-env-vars="AGENT_ENGINE_RESOURCE_NAME=projects/<PROJECT_NUMBER>/locations/us-central1/reasoningEngines/<RESOURCE_ID>,AGENT_DIRECTORY=app" \
  --allow-unauthenticated
```
