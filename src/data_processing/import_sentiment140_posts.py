from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.data_processing.paths import RAW_DATA_DIR
from src.domain.enums import ContentType
from src.domain.models import PostContentCreate
from src.services.content_service import ContentService


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV_PATH = RAW_DATA_DIR / "sentiment140" / "training.1600000.processed.noemoticon.csv"
DEFAULT_USERS_PATH = PROJECT_ROOT / "data" / "synthetic" / "users.json"

HASHTAG_PATTERN = re.compile(r"#(\w+)")


def load_user_ids(users_path: Path) -> list[str]:
    with users_path.open(encoding="utf-8") as users_file:
        users = json.load(users_file)
    return [user["_id"] for user in users]


def parse_tweet_date(value: str) -> datetime:
    parts = value.split()
    if len(parts) == 6:
        value = " ".join(parts[:4] + parts[5:])
    parsed = datetime.strptime(value, "%a %b %d %H:%M:%S %Y")
    return parsed.replace(tzinfo=UTC)


def sentiment_from_polarity(polarity: str) -> dict[str, Any]:
    if polarity == "0":
        return {"label": "negative", "score": 0.0, "polarity": 0}
    if polarity == "2":
        return {"label": "neutral", "score": 0.5, "polarity": 2}
    return {"label": "positive", "score": 1.0, "polarity": 4}


def extract_hashtags(text: str) -> list[str]:
    return [match.lower() for match in HASHTAG_PATTERN.findall(text)]


def map_author_to_user_id(author: str, user_ids: list[str], author_map: dict[str, str]) -> str:
    if author not in author_map:
        author_map[author] = user_ids[len(author_map) % len(user_ids)]
    return author_map[author]


def build_post(
    row: list[str],
    user_ids: list[str],
    author_map: dict[str, str],
) -> PostContentCreate:
    polarity, tweet_id, date_value, _query, author, text = row
    return PostContentCreate(
        type=ContentType.POST,
        author_id=map_author_to_user_id(author, user_ids, author_map),
        text=text,
        hashtags=extract_hashtags(text),
        source="sentiment140",
        external_id=tweet_id,
        sentiment=sentiment_from_polarity(polarity),
        created_at=parse_tweet_date(date_value),
    )


def import_sentiment140_posts(
    csv_path: Path,
    users_path: Path,
    limit: int,
    offset: int = 0,
    dry_run: bool = False,
) -> dict[str, int]:
    user_ids = load_user_ids(users_path)
    author_map: dict[str, str] = {}
    content_service = ContentService()
    processed = 0
    inserted = 0
    sentiment_counts = {"negative": 0, "neutral": 0, "positive": 0}

    with csv_path.open(encoding="latin1", newline="") as csv_file:
        reader = csv.reader(csv_file)
        for index, row in enumerate(reader):
            if index < offset:
                continue
            if processed >= limit:
                break
            if len(row) < 6:
                continue

            post = build_post(row, user_ids, author_map)
            sentiment_label = post.sentiment.label if post.sentiment else "neutral"
            sentiment_counts[sentiment_label] += 1

            if not dry_run:
                content_service.create_content(post)

            processed += 1
            inserted += 0 if dry_run else 1

    return {
        "processed": processed,
        "inserted": inserted,
        "negative": sentiment_counts["negative"],
        "neutral": sentiment_counts["neutral"],
        "positive": sentiment_counts["positive"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Sentiment140 tweets into the content collection as posts.")
    parser.add_argument("--csv-path", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--users-path", type=Path, default=DEFAULT_USERS_PATH)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.csv_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {args.csv_path}")
    if not args.users_path.exists():
        raise FileNotFoundError(f"Users file not found: {args.users_path}")

    result = import_sentiment140_posts(
        csv_path=args.csv_path,
        users_path=args.users_path,
        limit=args.limit,
        offset=args.offset,
        dry_run=args.dry_run,
    )
    print(result)


if __name__ == "__main__":
    main()
