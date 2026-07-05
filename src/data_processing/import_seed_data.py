from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.data_processing.import_restaurant_venues import import_restaurant_venues
from src.data_processing.paths import RESTAURANT_DATASET_PATH
from src.data_processing.import_sentiment140_posts import import_sentiment140_posts, load_user_ids
from src.domain.enums import ContentType, InteractionType
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


def load_json_list(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


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
) -> dict[str, Any]:
    restaurant_result = import_restaurant_venues(RESTAURANT_DATASET_PATH, dry_run=dry_run)
    user_ids = import_users(dry_run=dry_run)
    content_ids = import_synthetic_content(dry_run=dry_run)
    interactions_imported = import_synthetic_interactions(dry_run=dry_run)
    sentiment_result = import_sentiment140_posts(
        csv_path=PROJECT_ROOT / "data" / "raw" / "sentiment140" / "training.1600000.processed.noemoticon.csv",
        users_path=SYNTHETIC_USERS_PATH,
        limit=limit_sentiment140,
        dry_run=dry_run,
    )

    return {
        "restaurant_venues": restaurant_result,
        "users": len(user_ids),
        "synthetic_content": len(content_ids),
        "synthetic_interactions": interactions_imported,
        "sentiment140": sentiment_result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import all raw and synthetic seed data through the service layer.")
    parser.add_argument("--limit-sentiment140", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run_all(limit_sentiment140=args.limit_sentiment140, dry_run=args.dry_run)
    print(result)


if __name__ == "__main__":
    main()
