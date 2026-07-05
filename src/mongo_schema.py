import json
from pathlib import Path
from typing import Any

from pymongo import ASCENDING, DESCENDING, GEOSPHERE, IndexModel

from src.db import mongo_db


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = PROJECT_ROOT / "schema"

COLLECTION_SCHEMAS = {
    "activity_events": SCHEMA_ROOT / "ActivityEvents" / "activity_events.schema.json",
    "content": SCHEMA_ROOT / "Content" / "content.schema.json",
    "interactions": SCHEMA_ROOT / "Interactions" / "interactions.schema.json",
    "relationships": SCHEMA_ROOT / "Relationships" / "relationships.schema.json",
    "users": SCHEMA_ROOT / "Users" / "users.schema.json",
    "venues": SCHEMA_ROOT / "Venues" / "venues.schema.json",
}

COLLECTION_INDEXES = {
    "activity_events": [
        IndexModel([("created_at", ASCENDING)], name="activity_events_created_at_idx"),
        IndexModel([("type", ASCENDING), ("created_at", ASCENDING)], name="activity_events_type_created_at_idx"),
        IndexModel([("actor_user_id", ASCENDING), ("created_at", ASCENDING)], name="activity_events_actor_created_at_idx"),
        IndexModel(
            [("target_type", ASCENDING), ("target_id", ASCENDING), ("created_at", ASCENDING)],
            name="activity_events_target_created_at_idx",
        ),
    ],
    "content": [
        IndexModel([("created_at", ASCENDING)], name="content_created_at_idx"),
        IndexModel([("type", ASCENDING), ("created_at", ASCENDING)], name="content_type_created_at_idx"),
        IndexModel([("style", ASCENDING), ("created_at", ASCENDING)], name="content_style_created_at_idx"),
        IndexModel([("category", ASCENDING), ("created_at", ASCENDING)], name="content_category_created_at_idx"),
        IndexModel(
            [("sentiment.label", ASCENDING), ("created_at", ASCENDING)],
            name="content_sentiment_created_at_idx",
        ),
        IndexModel([("venue_id", ASCENDING), ("created_at", ASCENDING)], name="content_venue_created_at_idx"),
        IndexModel([("author_id", ASCENDING), ("created_at", ASCENDING)], name="content_author_created_at_idx"),
        IndexModel(
            [("parent_content_id", ASCENDING), ("created_at", ASCENDING)],
            name="content_parent_created_at_idx",
        ),
        IndexModel([("hashtags", ASCENDING), ("created_at", ASCENDING)], name="content_hashtags_created_at_idx"),
        IndexModel(
            [
                ("metrics.view_count", DESCENDING),
                ("metrics.like_count", DESCENDING),
                ("metrics.comment_count", DESCENDING),
            ],
            name="content_metrics_popularity_idx",
        ),
    ],
    "interactions": [
        IndexModel([("created_at", ASCENDING)], name="interactions_created_at_idx"),
        IndexModel([("source", ASCENDING), ("created_at", ASCENDING)], name="interactions_source_created_at_idx"),
        IndexModel([("content_id", ASCENDING), ("created_at", ASCENDING)], name="interactions_content_created_at_idx"),
        IndexModel([("user_id", ASCENDING), ("created_at", ASCENDING)], name="interactions_user_created_at_idx"),
        IndexModel(
            [("user_id", ASCENDING), ("content_id", ASCENDING), ("created_at", ASCENDING)],
            name="interactions_user_content_created_at_idx",
        ),
        IndexModel([("session_id", ASCENDING), ("created_at", ASCENDING)], name="interactions_session_created_at_idx"),
    ],
    "relationships": [
        IndexModel([("created_at", ASCENDING)], name="relationships_created_at_idx"),
        IndexModel([("type", ASCENDING), ("created_at", ASCENDING)], name="relationships_type_created_at_idx"),
        IndexModel(
            [
                ("type", ASCENDING),
                ("source_user_id", ASCENDING),
                ("target_type", ASCENDING),
                ("created_at", ASCENDING),
                ("target_id", ASCENDING),
            ],
            name="relationships_source_target_created_at_idx",
        ),
        IndexModel(
            [
                ("type", ASCENDING),
                ("target_type", ASCENDING),
                ("target_id", ASCENDING),
                ("created_at", ASCENDING),
                ("source_user_id", ASCENDING),
            ],
            name="relationships_target_source_created_at_idx",
        ),
        IndexModel(
            [("projection_status", ASCENDING), ("created_at", ASCENDING)],
            name="relationships_projection_status_created_at_idx",
        ),
    ],
    "users": [
        IndexModel([("created_at", ASCENDING)], name="users_created_at_idx"),
        IndexModel([("city", ASCENDING), ("created_at", ASCENDING)], name="users_city_created_at_idx"),
        IndexModel([("username", ASCENDING)], name="users_username_idx"),
    ],
    "venues": [
        IndexModel([("created_at", ASCENDING)], name="venues_created_at_idx"),
        IndexModel([("city", ASCENDING)], name="venues_city_idx"),
        IndexModel([("city", ASCENDING), ("category", ASCENDING)], name="venues_city_category_idx"),
        IndexModel([("category", ASCENDING)], name="venues_category_idx"),
        IndexModel([("cuisines", ASCENDING)], name="venues_cuisines_idx"),
        IndexModel(
            [("rating.aggregate_rating", DESCENDING), ("rating.votes", DESCENDING)],
            name="venues_rating_votes_idx",
        ),
        IndexModel(
            [("pricing.average_cost_for_two", ASCENDING), ("rating.aggregate_rating", DESCENDING)],
            name="venues_price_rating_idx",
        ),
        IndexModel([("location", GEOSPHERE)], name="venues_location_2dsphere_idx"),
    ],
}


def load_validator(schema_path: Path) -> dict[str, Any]:
    with schema_path.open(encoding="utf-8") as schema_file:
        return json.load(schema_file)


def apply_collection_validator(collection_name: str, validator: dict[str, Any]) -> str:
    existing_collections = mongo_db.list_collection_names()

    if collection_name in existing_collections:
        mongo_db.command(
            {
                "collMod": collection_name,
                "validator": validator,
                "validationLevel": "moderate",
                "validationAction": "error",
            }
        )
        return "updated"

    mongo_db.create_collection(
        collection_name,
        validator=validator,
        validationLevel="moderate",
        validationAction="error",
    )
    return "created"


def ensure_collection_indexes(collection_name: str) -> list[str]:
    indexes = COLLECTION_INDEXES.get(collection_name, [])
    if not indexes:
        return []
    return mongo_db[collection_name].create_indexes(indexes)


def initialize_mongodb_collections() -> dict[str, str]:
    results = {}

    for collection_name, schema_path in COLLECTION_SCHEMAS.items():
        validator = load_validator(schema_path)
        validator_status = apply_collection_validator(collection_name, validator)
        index_names = ensure_collection_indexes(collection_name)
        results[collection_name] = f"{validator_status}; indexes ensured: {len(index_names)}"

    return results
