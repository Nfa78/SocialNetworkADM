from __future__ import annotations

import json
import random
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from src.data_processing.paths import DATA_DIR


SEED = 42
TARGET_COUNT = 500
CONTENT_FILE = DATA_DIR / "synthetic" / "content.json"
INTERACTIONS_FILE = DATA_DIR / "synthetic" / "interactions.json"
RELATIONSHIPS_FILE = DATA_DIR / "synthetic" / "relationships.json"


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def assign_content_ids(content_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rewritten: list[dict[str, Any]] = []
    available_ids: list[str] = []
    base_time = datetime.now(UTC) - timedelta(days=120)
    for index, item in enumerate(content_items, start=1):
        content_id = f"content_{index:03d}"
        updated = dict(item)
        updated["_id"] = content_id
        updated["created_at"] = (base_time + timedelta(hours=index * 3)).isoformat()
        if updated.get("type") == "comment":
            parent_candidates = available_ids or [content_id]
            updated["parent_content_id"] = random.choice(parent_candidates)
        rewritten.append(updated)
        available_ids.append(content_id)
    return rewritten


def rewrite_interactions(interactions: list[dict[str, Any]], content_ids: list[str]) -> list[dict[str, Any]]:
    rewritten: list[dict[str, Any]] = []
    base_time = datetime.now(UTC) - timedelta(days=30)
    for index, item in enumerate(interactions, start=1):
        updated = dict(item)
        updated["content_id"] = content_ids[(index - 1) % len(content_ids)]
        updated["created_at"] = (base_time + timedelta(minutes=index * 17)).isoformat()
        rewritten.append(updated)
    return rewritten


def weighted_pick(items: list[str], alpha: float) -> str:
    weights = [1.0 / ((rank + 1) ** alpha) for rank in range(len(items))]
    return random.choices(items, weights=weights, k=1)[0]


def build_relationships(
    user_ids: list[str],
    content_ids: list[str],
    venue_ids: list[str],
    total_count: int = TARGET_COUNT,
) -> list[dict[str, Any]]:
    popular_users = user_ids[:25]
    popular_contents = content_ids[:40]
    popular_venues = venue_ids[:20]

    relationships: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    base_time = datetime.now(UTC) - timedelta(days=60)
    relationship_index = 0

    while len(relationships) < total_count:
        relation_type = random.choices(["like", "follow"], weights=[0.68, 0.32], k=1)[0]
        source_user_id = random.choice(user_ids)

        if relation_type == "like":
            target_type = "content"
            target_id = weighted_pick(popular_contents, alpha=1.18)
        else:
            target_type = random.choices(["user", "venue"], weights=[0.78, 0.22], k=1)[0]
            if target_type == "user":
                target_id = weighted_pick(popular_users, alpha=1.22)
                if target_id == source_user_id:
                    continue
            else:
                target_id = weighted_pick(popular_venues, alpha=1.16)

        key = (relation_type, source_user_id, target_id)
        if key in seen:
            continue
        seen.add(key)
        relationship_index += 1
        relationships.append(
            {
                "type": relation_type,
                "source_user_id": source_user_id,
                "target_type": target_type,
                "target_id": target_id,
                "created_at": (base_time + timedelta(hours=relationship_index * 2)).isoformat(),
            }
        )

    relationships.sort(key=lambda item: (item["type"], item["target_type"], item["source_user_id"], item["target_id"]))
    return relationships


def summarize_relationships(relationships: list[dict[str, Any]]) -> dict[str, Any]:
    type_counter = Counter(item["type"] for item in relationships)
    target_counter = Counter(item["target_type"] for item in relationships)
    content_targets = Counter(item["target_id"] for item in relationships if item["target_type"] == "content")
    user_targets = Counter(item["target_id"] for item in relationships if item["target_type"] == "user")
    venue_targets = Counter(item["target_id"] for item in relationships if item["target_type"] == "venue")

    return {
        "total": len(relationships),
        "by_type": dict(type_counter),
        "by_target_type": dict(target_counter),
        "top_content_targets": content_targets.most_common(10),
        "top_user_targets": user_targets.most_common(10),
        "top_venue_targets": venue_targets.most_common(10),
    }


def main() -> None:
    random.seed(SEED)

    users = load_json(DATA_DIR / "synthetic" / "users.json")
    content = load_json(CONTENT_FILE)
    interactions = load_json(INTERACTIONS_FILE)
    venues = load_json(DATA_DIR / "synthetic" / "venues.json") if (DATA_DIR / "synthetic" / "venues.json").exists() else []

    content = assign_content_ids(content)
    content_ids = [item["_id"] for item in content]
    if not venues:
        venue_ids = sorted({item.get("venue_id") for item in content if item.get("venue_id")})
    else:
        venue_ids = [item["_id"] for item in venues if "_id" in item]

    interactions = rewrite_interactions(interactions, content_ids)

    relationships = build_relationships(
        user_ids=[item["_id"] for item in users if "_id" in item],
        content_ids=content_ids,
        venue_ids=venue_ids,
        total_count=TARGET_COUNT,
    )

    save_json(CONTENT_FILE, content)
    save_json(INTERACTIONS_FILE, interactions)
    save_json(RELATIONSHIPS_FILE, relationships)

    summary = summarize_relationships(relationships)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
