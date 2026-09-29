# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from app.a2ui_utils import a2ui_callback
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types

PROJECT_ID = "qwiklabs-gcp-02-ffb8eb049f83"
COLLECTION_NAME = "plants"
BUCKET_NAME = "plant-care-helper-media-qwiklabs-gcp-02-ffb8eb049f83"
MEMORY_BANK_ID = "8385745936873160704"


async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location="us-central1",
        agent_engine_id=MEMORY_BANK_ID,
    )


def _get_agent_engine_resource_name() -> str:
    metadata_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "deployment_metadata.json",
    )
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                data = json.load(f)
                return data.get(
                    "remote_agent_runtime_id",
                    "projects/936731119517/locations/us-central1/reasoningEngines/4354918717260300288",
                )
        except Exception:
            pass
    return "projects/936731119517/locations/us-central1/reasoningEngines/4354918717260300288"


code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=_get_agent_engine_resource_name()
)


def _get_db():
    return firestore.Client(project=PROJECT_ID)


def search_plants_catalog(query: str = "") -> str:
    """Searches or lists plants in the catalog from the Firestore database.

    Args:
        query: Optional search term to filter plants by name, species, or light level.

    Returns:
        A list of matching plant records formatted as a string.
    """
    db = _get_db()
    docs = db.collection(COLLECTION_NAME).stream()
    results = []
    q = query.lower().strip()
    for doc in docs:
        data = doc.to_dict()
        if (
            not q
            or q in data.get("name", "").lower()
            or q in data.get("species", "").lower()
            or q in data.get("light_level", "").lower()
        ):
            results.append(data)
    if not results:
        return f"No plants found matching '{query}' in the catalog."
    return str(results)


def get_plant_details(plant_id: str) -> str:
    """Retrieves detailed care information for a specific plant by its ID from Firestore.

    Args:
        plant_id: The unique ID of the plant (e.g., 'monstera_deliciosa', 'snake_plant').

    Returns:
        The plant details dictionary formatted as a string, or an error if not found.
    """
    db = _get_db()
    doc_ref = db.collection(COLLECTION_NAME).document(plant_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Plant ID '{plant_id}' not found in the catalog."
    return str(doc.to_dict())


def log_plant_care(plant_id: str, action: str = "watered") -> str:
    """Logs a care action for a plant in Firestore (e.g. watering, fertilizing).

    Args:
        plant_id: The ID of the plant.
        action: The care action performed (e.g., 'watered', 'fertilized', 'pruned').

    Returns:
        Confirmation message of the logged care event.
    """
    db = _get_db()
    doc_ref = db.collection(COLLECTION_NAME).document(plant_id)
    doc = doc_ref.get()
    if not doc.exists:
        return f"Plant ID '{plant_id}' not found in the catalog."

    today_str = datetime.date.today().isoformat()
    updates = {}
    if action.lower() == "watered":
        updates["last_watered"] = today_str

    updates["last_care_action"] = f"{action} on {today_str}"
    doc_ref.update(updates)
    return f"Successfully logged '{action}' for plant '{plant_id}' on {today_str}."


def add_or_update_plant(
    plant_id: str,
    name: str,
    species: str,
    light_level: str,
    water_frequency_days: int,
    care_tips: str = "",
) -> str:
    """Adds a new plant or updates an existing plant record in Firestore.

    Args:
        plant_id: Unique identifier for the plant.
        name: Common name of the plant.
        species: Botanical/scientific species name.
        light_level: Light requirements (e.g. 'Bright Indirect', 'Low Light').
        water_frequency_days: Days between waterings (integer).
        care_tips: General care tips and instructions.

    Returns:
        Confirmation message of the operation.
    """
    db = _get_db()
    data = {
        "id": plant_id,
        "name": name,
        "species": species,
        "light_level": light_level,
        "water_frequency_days": water_frequency_days,
        "care_tips": care_tips,
        "last_watered": datetime.date.today().isoformat(),
    }
    db.collection(COLLECTION_NAME).document(plant_id).set(data, merge=True)
    return f"Successfully saved plant '{name}' (ID: {plant_id}) to Firestore."


def get_local_weather_and_humidity(location: str) -> str:
    """Fetches real-time local weather and relative humidity for a location to inform plant care.

    Args:
        location: City or location name (e.g. 'New York', 'Seattle', 'Tokyo').

    Returns:
        A string containing current temperature and humidity data.
    """
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(location)}&count=1&language=en&format=json"
        req = urllib.request.Request(
            geo_url, headers={"User-Agent": "PlantCareAgent/1.0"}
        )
        with urllib.request.urlopen(req) as resp:
            geo_data = json.loads(resp.read().decode())

        if not geo_data.get("results"):
            return f"Could not find coordinates for location: '{location}'."

        loc_info = geo_data["results"][0]
        lat, lon = loc_info["latitude"], loc_info["longitude"]
        city_name = loc_info.get("name", location)
        country = loc_info.get("country", "")

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m&temperature_unit=fahrenheit"
        req_w = urllib.request.Request(
            weather_url, headers={"User-Agent": "PlantCareAgent/1.0"}
        )
        with urllib.request.urlopen(req_w) as resp:
            w_data = json.loads(resp.read().decode())

        current = w_data.get("current", {})
        temp = current.get("temperature_2m")
        humidity = current.get("relative_humidity_2m")

        return f"Current weather in {city_name}, {country}: {temp}°F, {humidity}% relative humidity."
    except Exception as e:
        return f"Error fetching weather data for '{location}': {str(e)}"


def lookup_botanical_info(plant_query: str) -> str:
    """Looks up official botanical taxonomy, common names, and reference links for a plant species from iNaturalist.

    Args:
        plant_query: The common or scientific name of the plant species (e.g., 'Monstera deliciosa', 'Peace Lily').

    Returns:
        A string summarizing scientific name, common name, wikipedia URL, and photo URL.
    """
    try:
        url = f"https://api.inaturalist.org/v1/taxa?q={urllib.parse.quote(plant_query)}&taxon_id=47126&per_page=1"
        headers = {"User-Agent": "PlantCareAgent/1.0"}

        api_key = os.getenv("INATURALIST_API_KEY")
        if api_key:
            headers["Authorization"] = api_key

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())

        results = data.get("results", [])
        if not results:
            return f"No botanical records found for '{plant_query}'."

        item = results[0]
        sci_name = item.get("name", "Unknown")
        common_name = item.get("preferred_common_name", "N/A")
        wiki_url = item.get("wikipedia_url", "N/A")
        photo = item.get("default_photo", {}).get("medium_url", "N/A")

        return (
            f"Botanical Record for '{plant_query}':\n"
            f"- Scientific Name: {sci_name}\n"
            f"- Common Name: {common_name}\n"
            f"- Wikipedia Reference: {wiki_url}\n"
            f"- Photo: {photo}"
        )
    except Exception as e:
        return f"Error looking up botanical info for '{plant_query}': {str(e)}"


def geocode_address(address: str) -> str:
    """Converts a street address or place name into geographic coordinates using Google Maps Geocoding API.

    Args:
        address: The street address or location name to geocode.

    Returns:
        A string containing formatted address, latitude, and longitude.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={urllib.parse.quote(address)}&key={api_key}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())

        results = data.get("results", [])
        if not results:
            return f"No geocoding results found for address: '{address}'."

        first = results[0]
        fmt_addr = first.get("formatted_address", address)
        loc = first.get("geometry", {}).get("location", {})
        lat = loc.get("lat")
        lng = loc.get("lng")

        return f"Address: {fmt_addr}\nLocation: latitude={lat}, longitude={lng}"
    except Exception as e:
        return f"Error geocoding address '{address}': {str(e)}"


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "florist",
    radius_meters: float = 5000.0,
) -> str:
    """Finds nearby places (e.g. florists, plant nurseries, parks) using Google Places API (New).

    Args:
        latitude: Center point latitude.
        longitude: Center point longitude.
        place_type: Place type filter (e.g., 'florist', 'park', 'store', 'home_goods_store').
        radius_meters: Search radius in meters (default 5000 meters).

    Returns:
        A list of nearby places formatted as a string containing name, address, and coordinates.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    try:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        payload = {
            "includedTypes": [place_type],
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": radius_meters,
                }
            },
            "maxResultCount": 5,
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())

        places = data.get("places", [])
        if not places:
            return f"No nearby places of type '{place_type}' found within {radius_meters}m."

        results = []
        for p in places:
            name = p.get("displayName", {}).get("text", "Unknown Name")
            addr = p.get("formattedAddress", "Unknown Address")
            loc = p.get("location", {})
            results.append(
                f"- Name: {name}\n  Address: {addr}\n  Location: lat={loc.get('latitude')}, lng={loc.get('longitude')}"
            )

        return "Nearby Places:\n" + "\n".join(results)
    except Exception as e:
        return f"Error finding nearby places: {str(e)}"


def generate_plant_image(
    prompt: str, tool_context: ToolContext
) -> str:
    """Generates an image for an indoor plant, plant decor setup, or care concept using gemini-3.1-flash-lite-image in the global region.

    Args:
        prompt: Description of the plant or decor layout to generate (e.g. 'A healthy Monstera in a white ceramic pot by a sunny window').
        tool_context: ToolContext provided by the framework to save artifacts.

    Returns:
        The public Cloud Storage HTTPS URL of the generated image.
    """
    try:
        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="global",
        )

        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        parts = response.candidates[0].content.parts
        image_part = None
        for p in parts:
            if p.inline_data:
                image_part = p
                break

        if not image_part or not image_part.inline_data:
            return "Failed to generate image: No image data returned from model."

        image_bytes = image_part.inline_data.data
        mime_type = image_part.inline_data.mime_type or "image/jpeg"
        ext = "png" if "png" in mime_type else "jpg"

        timestamp = int(datetime.datetime.now().timestamp())
        filename = f"plant_decor_{timestamp}.{ext}"

        # 1. Save artifact for Playground Artifacts panel
        part_artifact = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=part_artifact)

        # 2. Upload bytes directly to public GCS bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
        return f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

    except Exception as e:
        return f"Error generating plant image: {str(e)}"


def generate_plant_video(
    prompt: str, tool_context: ToolContext
) -> str:
    """Generates a short video for indoor plants, plant growth timelapses, or care tutorials using gemini-omni-flash-preview in the global region.

    Args:
        prompt: Description of the plant video to generate (e.g. 'A timelapse of a Monstera leaf unfurling in morning sunlight').
        tool_context: ToolContext provided by the framework to save artifacts.

    Returns:
        The public Cloud Storage HTTPS URL of the generated video.
    """
    try:
        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="global",
        )

        operation = client.models.generate_videos(
            model="gemini-omni-flash-preview",
            prompt=prompt,
        )

        while not operation.done:
            time.sleep(10)
            operation = client.operations.get(operation)

        if not operation.response or not operation.response.generated_videos:
            return "Failed to generate video: No video returned from model operation."

        generated_video = operation.response.generated_videos[0]
        video_bytes = client.files.download(file=generated_video.video)

        if not video_bytes:
            return "Failed to download generated video bytes."

        timestamp = int(datetime.datetime.now().timestamp())
        filename = f"plant_video_{timestamp}.mp4"
        mime_type = "video/mp4"

        # 1. Save artifact for Playground Artifacts panel
        part_artifact = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename=filename, artifact=part_artifact)

        # 2. Upload bytes directly to public GCS bucket
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        return f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

    except Exception as e:
        return f"Error generating plant video: {str(e)}"


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are a knowledgeable plant care assistant. You help users manage, search, "
        "and care for their indoor plants using the Firestore plant database, look up botanical taxonomy via iNaturalist, "
        "adjust care recommendations based on local weather/humidity, geocode user addresses, find nearby plant nurseries and florists, "
        "and generate custom visual images and videos of plant decor, growth timelapses, and care setups. "
        "You remember the user's stated preferences, health facts, and allergies (such as plant/pollen allergies, pet toxicity concerns, "
        "or sensitivities) from previous conversations to personalize your responses and keep recommendations safe."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects. "
        "When executing Python code in the sandbox, DO NOT call any tool named google:ds_python_interpreter. "
        "Instead, write your Python code strictly inside ```python ... ``` markdown code blocks in your response text."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
    tools=[
        PreloadMemoryTool(),
        search_plants_catalog,
        get_plant_details,
        log_plant_care,
        add_or_update_plant,
        get_local_weather_and_humidity,
        lookup_botanical_info,
        geocode_address,
        find_nearby_places,
        generate_plant_image,
        generate_plant_video,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
