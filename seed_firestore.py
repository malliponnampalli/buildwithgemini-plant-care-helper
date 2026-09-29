"""Seed script for Firestore plant collection."""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-02-ffb8eb049f83"
COLLECTION_NAME = "plants"

INITIAL_PLANTS = [
    {
        "id": "monstera_deliciosa",
        "name": "Monstera Deliciosa",
        "species": "Monstera deliciosa",
        "light_level": "Bright Indirect",
        "water_frequency_days": 7,
        "last_watered": "2026-09-22",
        "care_tips": "Allow soil to dry out between waterings. Wipe leaves with a damp cloth.",
    },
    {
        "id": "snake_plant",
        "name": "Snake Plant",
        "species": "Dracaena trifasciata",
        "light_level": "Low to Bright Indirect",
        "water_frequency_days": 14,
        "last_watered": "2026-09-15",
        "care_tips": "Tolerates neglect. Avoid overwatering to prevent root rot.",
    },
    {
        "id": "peace_lily",
        "name": "Peace Lily",
        "species": "Spathiphyllum",
        "light_level": "Medium Indirect",
        "water_frequency_days": 5,
        "last_watered": "2026-09-25",
        "care_tips": "Keep soil consistently moist but not soggy. Leaves droop when thirsty.",
    },
    {
        "id": "fiddle_leaf_fig",
        "name": "Fiddle Leaf Fig",
        "species": "Ficus lyrata",
        "light_level": "Bright Indirect",
        "water_frequency_days": 7,
        "last_watered": "2026-09-24",
        "care_tips": "Needs bright light and consistent placement. Avoid drafty locations.",
    },
]


def seed_database():
    db = firestore.Client(project=PROJECT_ID)
    plants_ref = db.collection(COLLECTION_NAME)

    print(f"Seeding '{COLLECTION_NAME}' collection in project '{PROJECT_ID}'...")
    for plant in INITIAL_PLANTS:
        doc_ref = plants_ref.document(plant["id"])
        doc_ref.set(plant)
        print(f"  - Seeded plant: {plant['name']} (ID: {plant['id']})")

    print("Seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
