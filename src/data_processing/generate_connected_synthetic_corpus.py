from __future__ import annotations

import csv
import json
import math
import random
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from src.data_processing.paths import DATA_DIR, RESTAURANT_DATASET_PATH


SEED = 42
USER_COUNT = 10000
CONTENT_COUNT = 15000
INTERACTION_COUNT = 50000
RELATIONSHIP_COUNT = 30000
COMMUNITY_COUNT = 12

USERS_FILE = DATA_DIR / "synthetic" / "users.json"
CONTENT_FILE = DATA_DIR / "synthetic" / "content.json"
INTERACTIONS_FILE = DATA_DIR / "synthetic" / "interactions.json"
RELATIONSHIPS_FILE = DATA_DIR / "synthetic" / "relationships.json"

CITY_WEIGHTS: list[tuple[str, int]] = [
    ("Turin", 16),
    ("Milan", 15),
    ("Rome", 14),
    ("Bologna", 12),
    ("Florence", 11),
    ("Naples", 10),
    ("Venice", 8),
    ("Genoa", 7),
    ("Palermo", 7),
    ("Bari", 6),
]

USER_INTERESTS = [
    "pasta",
    "museums",
    "street_food",
    "galleries",
    "wine",
    "architecture",
    "coffee",
    "historic_centers",
    "desserts",
    "seafood",
    "markets",
    "travel",
    "culture",
    "photography",
    "events",
    "recipes",
    "music",
    "nightlife",
    "brunch",
    "local_businesses",
]

CONTENT_TOPICS = {
    "food": ["pasta", "street_food", "desserts", "seafood", "brunch", "wine"],
    "culture": ["museums", "galleries", "architecture", "historic_centers", "photography"],
    "social": ["events", "music", "nightlife", "travel", "markets"],
    "local": ["culture", "local_businesses", "recipes", "coffee", "food"],
}

POST_TEMPLATES = [
    "A strong local spot with a clear identity and a good flow.",
    "The atmosphere is busy but the place still feels well curated.",
    "Worth a second visit for the balance of quality and character.",
    "A good example of how the local scene keeps evolving.",
    "A compact place with a lot of personality and solid execution.",
]

POST_STYLES = [
    ("food", 28),
    ("culture", 18),
    ("travel", 16),
    ("lifestyle", 14),
    ("event", 12),
    ("guide", 12),
]

POST_CATEGORIES = {
    "food": "food",
    "culture": "culture",
    "travel": "travel",
    "lifestyle": "lifestyle",
    "event": "event",
    "guide": "guide",
}

REVIEW_TEMPLATES = [
    "Solid execution and a well-managed menu.",
    "Good value overall, with a few details that stand out.",
    "Reliable service and a space that works for group visits.",
    "The quality is consistent, especially for the price range.",
    "A place with room for improvement, but still worth tracking.",
]

COMMENT_TEMPLATES = [
    "That fits the area well.",
    "Makes sense as a recommendation.",
    "I’d expect this to do well over time.",
    "Interesting pick for this neighborhood.",
    "This line of reasoning checks out.",
]

SOURCE_WEIGHTS = [
    ("feed", 40),
    ("recommendation", 28),
    ("search", 12),
    ("profile", 10),
    ("venue", 6),
    ("direct", 4),
]


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


def weighted_choice(values: list[tuple[Any, float]]) -> Any:
    labels = [value for value, _ in values]
    weights = [weight for _, weight in values]
    return random.choices(labels, weights=weights, k=1)[0]


def load_restaurant_venues(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            restaurant_id = row.get("Restaurant ID") or row.get("\ufeffRestaurant ID")
            if not restaurant_id:
                continue
            votes = int(float(row.get("Votes") or 0))
            rating = float(row.get("Aggregate rating") or 0.0)
            longitude = float(row.get("Longitude") or 0.0)
            latitude = float(row.get("Latitude") or 0.0)
            rows.append(
                {
                    "_id": f"restaurant_{restaurant_id}",
                    "name": row.get("Restaurant Name", f"Restaurant {restaurant_id}"),
                    "city": row.get("City", "Unknown"),
                    "locality": row.get("Locality", row.get("City", "Unknown")),
                    "cuisines": [part.strip() for part in (row.get("Cuisines") or "").split(",") if part.strip()],
                    "votes": votes,
                    "rating": rating,
                    "longitude": longitude,
                    "latitude": latitude,
                }
            )
        return rows


def build_city_venues(venues: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for venue in venues:
        grouped[venue["city"]].append(venue)
    return grouped


def format_user_id(index: int) -> str:
    return f"user_{index:03d}" if index <= 999 else f"user_{index:04d}"


def format_content_id(index: int) -> str:
    return f"content_{index:03d}" if index <= 999 else f"content_{index:04d}"


def generate_users() -> tuple[list[dict[str, Any]], dict[str, float], dict[str, int], list[str]]:
    now = datetime.now(UTC)
    users: list[dict[str, Any]] = []
    user_scores: dict[str, float] = {}
    user_communities: dict[str, int] = {}

    for index in range(1, USER_COUNT + 1):
        user_id = format_user_id(index)
        community = (index - 1) % COMMUNITY_COUNT
        signup_age_days = int(random.betavariate(1.25, 1.9) * 540)
        created_at = now - timedelta(days=signup_age_days, minutes=random.randint(0, 24 * 60 - 1))
        users.append(
            {
                "_id": user_id,
                "username": user_id,
                "display_name": f"User {index:04d}",
                "city": weighted_choice(CITY_WEIGHTS),
                "interests": random.sample(USER_INTERESTS, k=3),
                "created_at": iso(created_at),
            }
        )
        user_communities[user_id] = community

    community_members: dict[int, list[str]] = defaultdict(list)
    for user in users:
        community_members[user_communities[user["_id"]]].append(user["_id"])

    for community, members in community_members.items():
        community_factor = 1.0 + (community * 0.03)
        for rank, user_id in enumerate(members):
            score = community_factor / ((rank + 1) ** 1.18)
            if rank == 0:
                score *= 6.0
            user_scores[user_id] = score

    hub_user_ids = [members[0] for _, members in sorted(community_members.items()) if members]
    return users, user_scores, user_communities, hub_user_ids


def select_text(template_pool: list[str]) -> str:
    return random.choice(template_pool)


def make_location_from_venue(venue: dict[str, Any], prefer_coordinates: bool = True) -> str | dict[str, Any]:
    if prefer_coordinates and random.random() < 0.7:
        return {
            "label": f"{venue['city']} / {venue['locality']}",
            "coordinates": {
                "latitude": venue["latitude"],
                "longitude": venue["longitude"],
            },
        }
    if random.random() < 0.5:
        return f"{venue['city']} / {venue['locality']}"
    return {
        "label": venue["city"],
        "coordinates": None,
    }


def normalize_tag(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def build_hashtags(
    author_interests: list[str],
    venue: dict[str, Any] | None,
    content_kind: str,
) -> list[str]:
    tags: list[str] = []
    if author_interests:
        tags.append(normalize_tag(random.choice(author_interests)))

    if venue is not None:
        cuisines = venue.get("cuisines") or []
        if cuisines:
            tags.append(normalize_tag(random.choice(cuisines)))
        tags.append(normalize_tag(venue["city"]))

    topic = random.choice(list(CONTENT_TOPICS.keys()))
    tags.extend(normalize_tag(tag) for tag in random.sample(CONTENT_TOPICS[topic], k=min(2, len(CONTENT_TOPICS[topic]))))
    if content_kind == "comment":
        tags.append("discussion")

    deduped: list[str] = []
    for tag in tags:
        if tag and tag not in deduped:
            deduped.append(tag)
    return deduped[:4]


def sentiment_payload(kind: str) -> dict[str, Any]:
    if kind == "review":
        label = random.choices(["positive", "neutral", "negative"], weights=[55, 30, 15], k=1)[0]
    elif kind == "comment":
        label = random.choices(["positive", "neutral", "negative"], weights=[35, 55, 10], k=1)[0]
    else:
        label = random.choices(["positive", "neutral", "negative"], weights=[40, 45, 15], k=1)[0]

    polarity_map = {"negative": -1, "neutral": 0, "positive": 1}
    score_map = {"negative": random.uniform(0.05, 0.45), "neutral": random.uniform(0.4, 0.65), "positive": random.uniform(0.6, 0.98)}
    return {
        "label": label,
        "score": round(score_map[label], 3),
        "polarity": polarity_map[label],
    }


def content_type_for_index(index: int) -> str:
    roll = random.random()
    if roll < 0.58:
        return "post"
    if roll < 0.84:
        return "review"
    return "comment"


def pick_post_style(author_interests: list[str], venue: dict[str, Any] | None) -> str:
    interests = {interest.lower() for interest in author_interests}
    if venue is not None:
        cuisines = {cuisine.lower() for cuisine in venue.get("cuisines", [])}
        if {"wine", "seafood", "street_food", "desserts"} & (interests | cuisines):
            return weighted_choice([(style, weight) for style, weight in POST_STYLES if style == "food" or style == "guide"])
        if {"museums", "galleries", "architecture", "historic_centers"} & interests:
            return weighted_choice([(style, weight) for style, weight in POST_STYLES if style in {"culture", "guide"}])
    return weighted_choice(POST_STYLES)


def pick_post_category(style: str) -> str:
    return POST_CATEGORIES.get(style, "general")


def build_content(
    users: list[dict[str, Any]],
    user_scores: dict[str, float],
    user_communities: dict[str, int],
    venues: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, float], dict[str, int]]:
    now = datetime.now(UTC)
    content_window_days = 365
    content_items: list[dict[str, Any]] = []
    content_scores: dict[str, float] = {}
    content_communities: dict[str, int] = {}

    users_by_id = {user["_id"]: user for user in users}
    user_weight_pool = [(user_id, score) for user_id, score in user_scores.items()]
    user_object_pool = [(user, user_scores[user["_id"]]) for user in users]
    community_members: dict[int, list[str]] = defaultdict(list)
    for user_id, community in user_communities.items():
        community_members[community].append(user_id)

    venues_by_city = build_city_venues(venues)
    venue_weights = [(venue, max(1.0, venue["votes"] + venue["rating"] * 15.0)) for venue in venues]

    for index in range(1, CONTENT_COUNT + 1):
        content_id = format_content_id(index)
        author_id = weighted_choice(user_weight_pool)
        author = users_by_id[author_id]
        author_city = author["city"]
        author_interests = author["interests"]
        author_community = user_communities[author_id]
        author_created_at = datetime.fromisoformat(author["created_at"])
        kind = content_type_for_index(index)
        if not content_items and kind == "comment":
            kind = random.choice(["post", "review"])
        type_factor = {"post": 1.0, "review": 0.85, "comment": 0.55}[kind]
        created_offset_days = int((index / CONTENT_COUNT) ** 1.35 * content_window_days)
        created_at = now - timedelta(days=content_window_days - created_offset_days, minutes=random.randint(0, 24 * 60 - 1))
        chosen_venue: dict[str, Any] | None = None
        location: str | dict[str, Any] | None = None
        venue_id: str | None = None

        if kind in {"post", "review"}:
            matching_venues = venues_by_city.get(author_city, [])
            if matching_venues and random.random() < 0.55:
                chosen_venue = weighted_choice([(venue, max(1.0, venue["votes"] + venue["rating"] * 15.0)) for venue in matching_venues])
            else:
                chosen_venue = weighted_choice(venue_weights)
            venue_id = chosen_venue["_id"]
            location = make_location_from_venue(chosen_venue, prefer_coordinates=True)
        else:
            if content_items:
                parent_candidates = content_items[-min(len(content_items), 1500):]
                parent_weights = [
                    (
                        item,
                        item["popularity_score"] * (1.0 + max(0.0, 1.0 - ((len(content_items) - item["sequence_index"]) / max(1, len(content_items))))),
                    )
                    for item in parent_candidates
                ]
                parent_item = weighted_choice(parent_weights)
                parent_content_id = parent_item["_id"]
                parent_created_at = datetime.fromisoformat(parent_item["created_at"])
                lag_days = random.randint(1, 90)
                created_at = min(now, parent_created_at + timedelta(days=lag_days, hours=random.randint(0, 23), minutes=random.randint(0, 59)))
                venue_id = parent_item.get("venue_id")
                chosen_venue = next((venue for venue in venues if venue["_id"] == venue_id), None) if venue_id else None
                location = make_location_from_venue(chosen_venue, prefer_coordinates=False) if chosen_venue else f"{author_city} / discussion"
            else:
                parent_content_id = None
                location = f"{author_city} / discussion"

        created_at = min(now, max(created_at, author_created_at + timedelta(days=random.randint(1, 120))))
        if kind == "comment" and content_items:
            created_at = min(now, max(created_at, parent_created_at + timedelta(days=random.randint(1, 90))))

        rating_value: int | None = None
        if kind == "post":
            style = pick_post_style(author_interests, chosen_venue)
            category = pick_post_category(style)
            text = select_text(POST_TEMPLATES)
        elif kind == "review":
            rating_value = random.choices([1, 2, 3, 4, 5], weights=[4, 8, 22, 32, 34], k=1)[0]
            text = select_text(REVIEW_TEMPLATES)
        else:
            text = select_text(COMMENT_TEMPLATES)

        hashtags = build_hashtags(author_interests, chosen_venue, kind)
        content_payload: dict[str, Any] = {
            "_id": content_id,
            "type": kind,
            "author_id": author_id,
            "text": text,
            "hashtags": hashtags,
            "location": location,
            "source": "synthetic",
            "created_at": iso(created_at),
        }

        if kind == "post":
            content_payload["style"] = style
            content_payload["category"] = category

        if chosen_venue is not None:
            content_payload["venue_id"] = venue_id

        if kind == "review":
            content_payload["rating"] = rating_value if rating_value is not None else 4
        if kind == "comment":
            content_payload["parent_content_id"] = parent_content_id

        content_payload["sentiment"] = sentiment_payload(kind)

        popularity_seed = user_scores[author_id] * type_factor
        if chosen_venue is not None:
            popularity_seed *= 1.0 + (chosen_venue["rating"] / 5.0)
            popularity_seed *= 1.0 + min(1.5, chosen_venue["votes"] / 1000.0)
        popularity_seed *= random.uniform(0.85, 1.35)
        if kind == "comment" and content_items:
            popularity_seed *= 0.55

        content_payload["sequence_index"] = index
        content_payload["popularity_score"] = popularity_seed
        content_payload["community"] = author_community
        content_items.append(content_payload)
        content_scores[content_id] = popularity_seed
        content_communities[content_id] = author_community

    return content_items, content_scores, content_communities


def build_interactions(
    users: list[dict[str, Any]],
    user_scores: dict[str, float],
    user_communities: dict[str, int],
    content_items: list[dict[str, Any]],
    content_scores: dict[str, float],
    content_communities: dict[str, int],
) -> list[dict[str, Any]]:
    now = datetime.now(UTC)
    interactions: list[dict[str, Any]] = []
    users_by_id = {user["_id"]: user for user in users}
    content_list = list(content_items)
    user_weight_pool = [(user_id, score) for user_id, score in user_scores.items()]
    user_object_pool = [(user, user_scores[user["_id"]]) for user in users]
    content_weight_pool = [(item, content_scores[item["_id"]]) for item in content_list]

    def interaction_timestamp(content_item: dict[str, Any], user_id: str, extra_days: int = 0) -> datetime:
        content_created_at = datetime.fromisoformat(content_item["created_at"])
        user_created_at = datetime.fromisoformat(users_by_id[user_id]["created_at"])
        lag = timedelta(days=random.randint(0, 120) + extra_days, minutes=random.randint(0, 23 * 60))
        return min(now, max(content_created_at, user_created_at) + lag)

    source_pool = [(source, weight) for source, weight in SOURCE_WEIGHTS]

    # Guarantee coverage: one view per content item.
    for content_item in content_list:
        same_community_users = [user_id for user_id, community in user_communities.items() if community == content_item["community"]]
        user_id = weighted_choice([(user_id, user_scores[user_id]) for user_id in same_community_users]) if same_community_users else weighted_choice(user_weight_pool)
        created_at = interaction_timestamp(content_item, user_id, extra_days=1)
        interactions.append(
            {
                "type": "view",
                "user_id": user_id,
                "content_id": content_item["_id"],
                "source": weighted_choice(source_pool),
                "session_id": f"session_{len(interactions) + 1:06d}",
                "duration_ms": random.randint(3000, 120000),
                "created_at": iso(created_at),
            }
        )

    # Guarantee coverage: one view per user.
    top_content_items = sorted(content_list, key=lambda item: content_scores[item["_id"]], reverse=True)[:max(100, len(content_list) // 10)]
    for index, user in enumerate(users, start=1):
        target_item = weighted_choice([(item, content_scores[item["_id"]]) for item in top_content_items])
        created_at = interaction_timestamp(target_item, user["_id"], extra_days=2)
        interactions.append(
            {
                "type": "view",
                "user_id": user["_id"],
                "content_id": target_item["_id"],
                "source": weighted_choice(source_pool),
                "session_id": f"session_{len(interactions) + 1:06d}",
                "duration_ms": random.randint(2000, 90000),
                "created_at": iso(created_at),
            }
        )

    remaining = INTERACTION_COUNT - len(interactions)
    for _ in range(max(0, remaining)):
        user_id = weighted_choice(user_weight_pool)
        source = weighted_choice(source_pool)
        content_item = weighted_choice(content_weight_pool)
        created_at = interaction_timestamp(content_item, user_id, extra_days=random.randint(0, 60))
        interactions.append(
            {
                "type": "view",
                "user_id": user_id,
                "content_id": content_item["_id"],
                "source": source,
                "session_id": f"session_{len(interactions) + 1:06d}",
                "duration_ms": random.randint(1000, 180000),
                "created_at": iso(created_at),
            }
        )

    random.shuffle(interactions)
    return interactions[:INTERACTION_COUNT]


def build_relationships(
    users: list[dict[str, Any]],
    user_scores: dict[str, float],
    user_communities: dict[str, int],
    hub_user_ids: list[str],
    content_items: list[dict[str, Any]],
    content_scores: dict[str, float],
    content_communities: dict[str, int],
    venues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    now = datetime.now(UTC)
    relationships: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    users_by_id = {user["_id"]: user for user in users}
    content_list = list(content_items)
    user_weight_pool = [(user_id, score) for user_id, score in user_scores.items()]
    user_object_pool = [(user, user_scores[user["_id"]]) for user in users]
    content_weight_pool = [(item, content_scores[item["_id"]]) for item in content_list]
    venue_weights = [(venue, max(1.0, venue["votes"] + venue["rating"] * 15.0)) for venue in venues]

    def add_relationship(
        relation_type: str,
        source_user_id: str,
        target_type: str,
        target_id: str,
        created_at: datetime,
    ) -> None:
        key = (relation_type, source_user_id, target_id)
        if key in seen:
            return
        seen.add(key)
        relationships.append(
            {
                "type": relation_type,
                "source_user_id": source_user_id,
                "target_type": target_type,
                "target_id": target_id,
                "created_at": iso(created_at),
            }
        )

    # Backbone for connectivity: each user follows a community hub.
    community_hub_by_user: dict[int, str] = {}
    for hub_id in hub_user_ids:
        community = user_communities[hub_id]
        community_hub_by_user[community] = hub_id

    for user in users:
        source_id = user["_id"]
        community = user_communities[source_id]
        hub_id = community_hub_by_user[community]
        if source_id != hub_id:
            source_created_at = datetime.fromisoformat(user["created_at"])
            target_created_at = datetime.fromisoformat(users_by_id[hub_id]["created_at"])
            created_at = max(source_created_at, target_created_at) + timedelta(days=random.randint(1, 240), hours=random.randint(0, 23))
            add_relationship("follow", source_id, "user", hub_id, min(now, created_at))

    # Connect hubs together in a ring.
    for index, hub_id in enumerate(hub_user_ids):
        next_hub_id = hub_user_ids[(index + 1) % len(hub_user_ids)]
        source_created_at = datetime.fromisoformat(users_by_id[hub_id]["created_at"])
        target_created_at = datetime.fromisoformat(users_by_id[next_hub_id]["created_at"])
        created_at = max(source_created_at, target_created_at) + timedelta(days=random.randint(10, 300), hours=random.randint(0, 23))
        add_relationship("follow", hub_id, "user", next_hub_id, min(now, created_at))

    popular_content_pool = sorted(content_list, key=lambda item: content_scores[item["_id"]], reverse=True)
    popular_user_pool = sorted(users, key=lambda user: user_scores[user["_id"]], reverse=True)
    popular_venue_pool = sorted(venues, key=lambda venue: venue["votes"] + venue["rating"] * 15.0, reverse=True)

    attempts = 0
    while len(relationships) < RELATIONSHIP_COUNT and attempts < RELATIONSHIP_COUNT * 20:
        attempts += 1
        relation_type = random.choices(["like", "follow"], weights=[0.64, 0.36], k=1)[0]
        source_user = weighted_choice(user_object_pool)
        source_id = source_user["_id"]
        source_created_at = datetime.fromisoformat(source_user["created_at"])

        if relation_type == "like":
            target_item = weighted_choice([(item, content_scores[item["_id"]]) for item in popular_content_pool[: max(300, len(popular_content_pool) // 5)]])
            target_created_at = datetime.fromisoformat(target_item["created_at"])
            lag = timedelta(days=random.randint(0, 210), hours=random.randint(0, 23))
            created_at = min(now, max(source_created_at, target_created_at) + lag)
            add_relationship("like", source_id, "content", target_item["_id"], created_at)
            continue

        target_type = random.choices(["user", "venue"], weights=[0.83, 0.17], k=1)[0]
        if target_type == "user":
            if random.random() < 0.72:
                same_community_users = [user for user in users if user_communities[user["_id"]] == user_communities[source_id] and user["_id"] != source_id]
                if same_community_users:
                    target_user = weighted_choice([(user, user_scores[user["_id"]]) for user in same_community_users])
                else:
                    target_user = weighted_choice([(user, user_scores[user["_id"]]) for user in popular_user_pool])
            else:
                target_user = weighted_choice([(user, user_scores[user["_id"]]) for user in popular_user_pool])
            if target_user["_id"] == source_id:
                continue
            target_created_at = datetime.fromisoformat(target_user["created_at"])
            lag = timedelta(days=random.randint(0, 300), hours=random.randint(0, 23))
            created_at = min(now, max(source_created_at, target_created_at) + lag)
            add_relationship("follow", source_id, "user", target_user["_id"], created_at)
        else:
            if not popular_venue_pool:
                continue
            target_venue = weighted_choice([(venue, max(1.0, venue["votes"] + venue["rating"] * 15.0)) for venue in popular_venue_pool[:250]])
            created_at = source_created_at + timedelta(days=random.randint(0, 360), hours=random.randint(0, 23))
            add_relationship("follow", source_id, "venue", target_venue["_id"], min(now, created_at))

    relationships.sort(key=lambda item: (item["created_at"], item["type"], item["source_user_id"], item["target_id"]))
    return relationships[:RELATIONSHIP_COUNT]


def summarize_dataset(
    users: list[dict[str, Any]],
    content_items: list[dict[str, Any]],
    interactions: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
) -> dict[str, Any]:
    def counts(items: list[dict[str, Any]], key: str) -> dict[str, int]:
        result: dict[str, int] = defaultdict(int)
        for item in items:
            result[item[key]] += 1
        return dict(result)

    content_types = counts(content_items, "type")
    relationship_types = counts(relationships, "type")
    relationship_targets = counts(relationships, "target_type")
    return {
        "users": len(users),
        "content": len(content_items),
        "interactions": len(interactions),
        "relationships": len(relationships),
        "content_types": content_types,
        "relationship_types": relationship_types,
        "relationship_targets": relationship_targets,
        "top_like_targets": sorted(
            [(item["_id"], item["popularity_score"]) for item in content_items],
            key=lambda pair: pair[1],
            reverse=True,
        )[:10],
    }


def save_json(path: Path, payload: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main() -> None:
    random.seed(SEED)

    venues = load_restaurant_venues(RESTAURANT_DATASET_PATH)
    users, user_scores, user_communities, hub_user_ids = generate_users()
    content_items, content_scores, content_communities = build_content(users, user_scores, user_communities, venues)
    interactions = build_interactions(users, user_scores, user_communities, content_items, content_scores, content_communities)
    relationships = build_relationships(
        users,
        user_scores,
        user_communities,
        hub_user_ids,
        content_items,
        content_scores,
        content_communities,
        venues,
    )

    public_content_items = [
        {
            key: value
            for key, value in content_item.items()
            if key not in {"sequence_index", "popularity_score", "community"}
        }
        for content_item in content_items
    ]

    save_json(USERS_FILE, users)
    save_json(CONTENT_FILE, public_content_items)
    save_json(INTERACTIONS_FILE, interactions)
    save_json(RELATIONSHIPS_FILE, relationships)

    print(json.dumps(summarize_dataset(users, content_items, interactions, relationships), indent=2))


if __name__ == "__main__":
    main()
