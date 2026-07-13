from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.data_processing.import_relationships import import_relationships
from src.data_processing.import_restaurant_venues import import_restaurant_venues
from src.data_processing.import_sentiment140_posts import import_sentiment140_posts
from src.data_processing.paths import RESTAURANT_DATASET_PATH, RAW_DATA_DIR
from src.domain.enums import ContentType
from src.domain.models import (
    CommentContentCreate,
    ContentCreate,
    InteractionCreate,
    PostContentCreate,
    ReviewContentCreate,
    UserCreate,
)
from src.services.content_service import ContentService
from src.services.interaction_service import InteractionService
from src.services.user_service import UserService


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_USERS_PATH = PROJECT_ROOT / "data" / "synthetic" / "users.json"
SYNTHETIC_CONTENT_PATH = PROJECT_ROOT / "data" / "synthetic" / "content.json"
SYNTHETIC_INTERACTIONS_PATH = PROJECT_ROOT / "data" / "synthetic" / "interactions.json"
SYNTHETIC_RELATIONSHIPS_PATH = PROJECT_ROOT / "data" / "synthetic" / "relationships.json"
SENTIMENT140_PATH = RAW_DATA_DIR / "sentiment140" / "training.1600000.processed.noemoticon.csv"

RESTAURANT_FIELDNAMES = [
    "Restaurant ID",
    "Restaurant Name",
    "Country Code",
    "City",
    "Address",
    "Locality",
    "Locality Verbose",
    "Longitude",
    "Latitude",
    "Cuisines",
    "Average Cost for two",
    "Currency",
    "Price range",
    "Has Table booking",
    "Has Online delivery",
    "Is delivering now",
    "Aggregate rating",
    "Rating color",
    "Rating text",
    "Votes",
]

SAMPLE_RESTAURANTS = [
    {
        "Restaurant ID": "900001",
        "Restaurant Name": "Demo Trattoria Centrale",
        "Country Code": "IT",
        "City": "Turin",
        "Address": "Via Roma 1",
        "Locality": "Centro",
        "Locality Verbose": "Centro, Turin",
        "Longitude": "7.6869",
        "Latitude": "45.0703",
        "Cuisines": "Italian, Cafe",
        "Average Cost for two": "45",
        "Currency": "EUR",
        "Price range": "2",
        "Has Table booking": "Yes",
        "Has Online delivery": "No",
        "Is delivering now": "No",
        "Aggregate rating": "4.4",
        "Rating color": "Green",
        "Rating text": "Very Good",
        "Votes": "420",
    },
    {
        "Restaurant ID": "900002",
        "Restaurant Name": "Demo Navigli Bites",
        "Country Code": "IT",
        "City": "Milan",
        "Address": "Ripa di Porta Ticinese 10",
        "Locality": "Navigli",
        "Locality Verbose": "Navigli, Milan",
        "Longitude": "9.1750",
        "Latitude": "45.4510",
        "Cuisines": "Street Food, Italian",
        "Average Cost for two": "38",
        "Currency": "EUR",
        "Price range": "2",
        "Has Table booking": "No",
        "Has Online delivery": "Yes",
        "Is delivering now": "Yes",
        "Aggregate rating": "4.1",
        "Rating color": "Green",
        "Rating text": "Good",
        "Votes": "310",
    },
    {
        "Restaurant ID": "900003",
        "Restaurant Name": "Demo Roma Osteria",
        "Country Code": "IT",
        "City": "Rome",
        "Address": "Via del Corso 20",
        "Locality": "Centro Storico",
        "Locality Verbose": "Centro Storico, Rome",
        "Longitude": "12.4823",
        "Latitude": "41.8933",
        "Cuisines": "Roman, Italian",
        "Average Cost for two": "50",
        "Currency": "EUR",
        "Price range": "3",
        "Has Table booking": "Yes",
        "Has Online delivery": "No",
        "Is delivering now": "No",
        "Aggregate rating": "4.6",
        "Rating color": "Green",
        "Rating text": "Excellent",
        "Votes": "530",
    },
    {
        "Restaurant ID": "900004",
        "Restaurant Name": "Demo New Delhi Kitchen",
        "Country Code": "IN",
        "City": "New Delhi",
        "Address": "Connaught Place",
        "Locality": "Connaught Place",
        "Locality Verbose": "Connaught Place, New Delhi",
        "Longitude": "77.2197",
        "Latitude": "28.6328",
        "Cuisines": "North Indian, Cafe",
        "Average Cost for two": "1200",
        "Currency": "INR",
        "Price range": "3",
        "Has Table booking": "Yes",
        "Has Online delivery": "Yes",
        "Is delivering now": "No",
        "Aggregate rating": "4.2",
        "Rating color": "Green",
        "Rating text": "Very Good",
        "Votes": "880",
    },
]


def load_json_list(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json_list(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def write_sample_restaurant_dataset(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=RESTAURANT_FIELDNAMES)
        writer.writeheader()
        writer.writerows(SAMPLE_RESTAURANTS)


def write_sample_sentiment140(path: Path, users: list[dict[str, Any]]) -> None:
    authors = [user["username"] for user in users[:6]] or ["demo_user"]
    rows = [
        ["4", "demo_tweet_001", "Mon Apr 06 22:19:45 2009", "NO_QUERY", authors[0], "Great local food discovery #food"],
        ["0", "demo_tweet_002", "Mon Apr 06 22:20:45 2009", "NO_QUERY", authors[1 % len(authors)], "Service was slow today #review"],
        ["4", "demo_tweet_003", "Mon Apr 06 22:21:45 2009", "NO_QUERY", authors[2 % len(authors)], "Loved this cultural walk #travel"],
        ["2", "demo_tweet_004", "Mon Apr 06 22:22:45 2009", "NO_QUERY", authors[3 % len(authors)], "Interesting place near the station"],
        ["4", "demo_tweet_005", "Mon Apr 06 22:23:45 2009", "NO_QUERY", authors[4 % len(authors)], "Worth bookmarking for dinner #italian"],
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="latin1", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerows(rows)


def sample_timestamp(day: int, hour: int = 12) -> str:
    return datetime(2026, 1, day, hour, 0, tzinfo=UTC).isoformat()


def build_sample_users() -> list[dict[str, Any]]:
    cities = ["Turin", "Milan", "Rome", "Bologna", "Florence", "Naples"]
    interests = [
        ["food", "coffee", "culture"],
        ["travel", "street_food", "photography"],
        ["museums", "architecture", "wine"],
        ["events", "nightlife", "markets"],
        ["desserts", "recipes", "local_businesses"],
        ["seafood", "historic_centers", "brunch"],
    ]
    return [
        {
            "_id": f"user_demo_{index + 1:03d}",
            "username": f"user_demo_{index + 1:03d}",
            "display_name": f"Demo User {index + 1}",
            "city": cities[index],
            "interests": interests[index],
            "created_at": sample_timestamp(index + 1, 9),
        }
        for index in range(len(cities))
    ]


def read_restaurant_venue_ids(path: Path, limit: int = 4) -> list[str]:
    if not path.exists():
        return []
    venue_ids: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            restaurant_id = row.get("Restaurant ID") or row.get("\ufeffRestaurant ID")
            if not restaurant_id:
                continue
            venue_ids.append(f"restaurant_{restaurant_id.strip()}")
            if len(venue_ids) >= limit:
                break
    return venue_ids


def build_sample_content(users: list[dict[str, Any]], venue_ids: list[str]) -> list[dict[str, Any]]:
    user_ids = [user["_id"] for user in users]
    padded_venue_ids = [*venue_ids, "restaurant_900001", "restaurant_900002", "restaurant_900003", "restaurant_900004"][:4]
    return [
        {
            "_id": "content_demo_001",
            "type": "post",
            "author_id": user_ids[0],
            "text": "A compact guide to a reliable central lunch spot.",
            "style": "food",
            "category": "food",
            "venue_id": padded_venue_ids[0],
            "hashtags": ["food", "turin", "lunch"],
            "source": "sample_synthetic",
            "sentiment": {"label": "positive", "score": 0.9, "polarity": 4},
            "created_at": sample_timestamp(7, 11),
        },
        {
            "_id": "content_demo_002",
            "type": "review",
            "author_id": user_ids[1],
            "venue_id": padded_venue_ids[1],
            "text": "Good street food and fast service near the canal.",
            "rating": 4,
            "hashtags": ["milan", "street_food"],
            "source": "sample_synthetic",
            "sentiment": {"label": "positive", "score": 0.8, "polarity": 4},
            "created_at": sample_timestamp(8, 13),
        },
        {
            "_id": "content_demo_003",
            "type": "post",
            "author_id": user_ids[2],
            "text": "A short route for food and architecture in the historic center.",
            "style": "travel",
            "category": "travel",
            "venue_id": padded_venue_ids[2],
            "hashtags": ["rome", "travel", "architecture"],
            "source": "sample_synthetic",
            "sentiment": {"label": "positive", "score": 0.85, "polarity": 4},
            "created_at": sample_timestamp(9, 10),
        },
        {
            "_id": "content_demo_004",
            "type": "post",
            "author_id": user_ids[3],
            "text": "A New Delhi venue with strong engagement signals for the map demo.",
            "style": "food",
            "category": "food",
            "venue_id": padded_venue_ids[3],
            "hashtags": ["newdelhi", "food"],
            "source": "sample_synthetic",
            "sentiment": {"label": "neutral", "score": 0.5, "polarity": 2},
            "created_at": sample_timestamp(10, 15),
        },
        {
            "_id": "content_demo_005",
            "type": "comment",
            "author_id": user_ids[4],
            "parent_content_id": "content_demo_001",
            "text": "This works well as a recommendation anchor.",
            "hashtags": ["recommendation"],
            "source": "sample_synthetic",
            "sentiment": {"label": "positive", "score": 0.7, "polarity": 4},
            "created_at": sample_timestamp(11, 16),
        },
        {
            "_id": "content_demo_006",
            "type": "review",
            "author_id": user_ids[5],
            "venue_id": padded_venue_ids[0],
            "text": "Consistent quality and a useful central location.",
            "rating": 5,
            "hashtags": ["turin", "review"],
            "source": "sample_synthetic",
            "sentiment": {"label": "positive", "score": 1.0, "polarity": 4},
            "created_at": sample_timestamp(12, 18),
        },
    ]


def build_sample_interactions(users: list[dict[str, Any]], content: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sources = ["feed", "recommendation", "search", "profile", "venue", "direct"]
    for index in range(36):
        rows.append(
            {
                "type": "view",
                "user_id": users[index % len(users)]["_id"],
                "content_id": content[(index * 2) % len(content)]["_id"],
                "source": sources[index % len(sources)],
                "session_id": f"sample_session_{index + 1:04d}",
                "duration_ms": 5000 + index * 1750,
                "created_at": sample_timestamp(13 + (index % 10), 8 + (index % 10)),
            }
        )
    return rows


def build_sample_relationships(users: list[dict[str, Any]], content: list[dict[str, Any]], venue_ids: list[str]) -> list[dict[str, Any]]:
    user_ids = [user["_id"] for user in users]
    content_ids = [item["_id"] for item in content]
    padded_venue_ids = [*venue_ids, "restaurant_900001", "restaurant_900002"][:2]
    rows: list[dict[str, Any]] = []
    for index, user_id in enumerate(user_ids):
        rows.append(
            {
                "type": "follow",
                "source_user_id": user_id,
                "target_type": "user",
                "target_id": user_ids[(index + 1) % len(user_ids)],
                "created_at": sample_timestamp(20 + index, 10),
            }
        )
        rows.append(
            {
                "type": "like",
                "source_user_id": user_id,
                "target_type": "content",
                "target_id": content_ids[index % len(content_ids)],
                "created_at": sample_timestamp(20 + index, 12),
            }
        )
    rows.extend(
        [
            {
                "type": "follow",
                "source_user_id": user_ids[0],
                "target_type": "venue",
                "target_id": padded_venue_ids[0],
                "created_at": sample_timestamp(25, 10),
            },
            {
                "type": "follow",
                "source_user_id": user_ids[1],
                "target_type": "venue",
                "target_id": padded_venue_ids[1],
                "created_at": sample_timestamp(25, 11),
            },
            {
                "type": "like",
                "source_user_id": user_ids[2],
                "target_type": "content",
                "target_id": "content_demo_001",
                "created_at": sample_timestamp(25, 12),
            },
        ]
    )
    return rows


def ensure_seed_inputs(auto_generate_missing: bool = True) -> dict[str, str]:
    status: dict[str, str] = {}

    if RESTAURANT_DATASET_PATH.exists():
        status["restaurant_dataset"] = "found"
    elif auto_generate_missing:
        write_sample_restaurant_dataset(RESTAURANT_DATASET_PATH)
        status["restaurant_dataset"] = "generated_sample"
    else:
        raise FileNotFoundError(f"Dataset file not found: {RESTAURANT_DATASET_PATH}")

    sample_users = build_sample_users()
    venue_ids = read_restaurant_venue_ids(RESTAURANT_DATASET_PATH)
    sample_content = build_sample_content(sample_users, venue_ids)
    sample_interactions = build_sample_interactions(sample_users, sample_content)
    sample_relationships = build_sample_relationships(sample_users, sample_content, venue_ids)
    synthetic_samples = {
        SYNTHETIC_USERS_PATH: ("synthetic_users", sample_users),
        SYNTHETIC_CONTENT_PATH: ("synthetic_content", sample_content),
        SYNTHETIC_INTERACTIONS_PATH: ("synthetic_interactions", sample_interactions),
        SYNTHETIC_RELATIONSHIPS_PATH: ("synthetic_relationships", sample_relationships),
    }

    for path, (key, rows) in synthetic_samples.items():
        if path.exists():
            status[key] = "found"
            continue
        if not auto_generate_missing:
            raise FileNotFoundError(f"Seed file not found: {path}")
        write_json_list(path, rows)
        status[key] = "generated_sample"

    if SENTIMENT140_PATH.exists():
        status["sentiment140"] = "found"
    elif auto_generate_missing:
        users = load_json_list(SYNTHETIC_USERS_PATH)
        write_sample_sentiment140(SENTIMENT140_PATH, users)
        status["sentiment140"] = "generated_sample"
    else:
        raise FileNotFoundError(f"Dataset file not found: {SENTIMENT140_PATH}")

    return status


def build_user_create(row: dict[str, Any]) -> UserCreate:
    return UserCreate.model_validate(row)


def import_users(users_path: Path = SYNTHETIC_USERS_PATH, dry_run: bool = False) -> list[str]:
    user_service = UserService()
    user_ids: list[str] = []
    for row in load_json_list(users_path):
        user = build_user_create(row)
        created = user_service.upsert_user(user) if not dry_run else UserCreate.model_validate(row)
        user_ids.append(created.id if not dry_run else (user.id or row["_id"]))
    return user_ids


def build_content_create(row: dict[str, Any]) -> ContentCreate:
    content_type = row["type"]
    if content_type == ContentType.POST:
        return PostContentCreate.model_validate(row)
    if content_type == ContentType.REVIEW:
        return ReviewContentCreate.model_validate(row)
    if content_type == ContentType.COMMENT:
        return CommentContentCreate.model_validate(row)
    raise ValueError(f"Unsupported content type: {content_type}")


def import_synthetic_content(
    content_path: Path = SYNTHETIC_CONTENT_PATH,
    dry_run: bool = False,
) -> list[str]:
    content_service = ContentService()
    created_ids: list[str] = []

    rows = load_json_list(content_path)
    for index, row in enumerate(rows):
        content = build_content_create(row)
        if dry_run:
            created_ids.append(f"dry_run_{index:03d}")
            continue

        created = content_service.create_content(content)
        created_ids.append(created.id)

    return created_ids


def import_synthetic_interactions(
    interactions_path: Path = SYNTHETIC_INTERACTIONS_PATH,
    dry_run: bool = False,
) -> int:
    interaction_service = InteractionService()
    rows = load_json_list(interactions_path)
    imported = 0

    for row in rows:
        interaction = InteractionCreate.model_validate(row)
        if not dry_run:
            interaction_service.create_interaction(interaction)
        imported += 1

    return imported


def run_all(
    limit_sentiment140: int,
    dry_run: bool = False,
    auto_generate_missing: bool = True,
) -> dict[str, Any]:
    seed_inputs = ensure_seed_inputs(auto_generate_missing=auto_generate_missing)
    restaurant_result = import_restaurant_venues(RESTAURANT_DATASET_PATH, dry_run=dry_run)
    user_ids = import_users(dry_run=dry_run)
    content_ids = import_synthetic_content(dry_run=dry_run)
    relationship_result = import_relationships(SYNTHETIC_RELATIONSHIPS_PATH, dry_run=dry_run)
    interactions_imported = import_synthetic_interactions(dry_run=dry_run)
    sentiment_result = import_sentiment140_posts(
        csv_path=SENTIMENT140_PATH,
        users_path=SYNTHETIC_USERS_PATH,
        limit=limit_sentiment140,
        dry_run=dry_run,
    )

    return {
        "seed_inputs": seed_inputs,
        "restaurant_venues": restaurant_result,
        "users": len(user_ids),
        "synthetic_content": len(content_ids),
        "synthetic_relationships": relationship_result,
        "synthetic_interactions": interactions_imported,
        "sentiment140": sentiment_result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import all raw and synthetic seed data through the service layer.")
    parser.add_argument("--limit-sentiment140", type=int, default=1000)
    parser.add_argument(
        "--no-auto-generate-missing-data",
        action="store_true",
        help="Fail instead of creating compact sample files when expected seed files are missing.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run_all(
        limit_sentiment140=args.limit_sentiment140,
        dry_run=args.dry_run,
        auto_generate_missing=not args.no_auto_generate_missing_data,
    )
    print(result)


if __name__ == "__main__":
    main()
