from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.data_processing.paths import DATA_DIR


SEED = 42
USER_COUNT = 5000
USERS_FILE = DATA_DIR / "synthetic" / "users.json"

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

INTEREST_POOL = [
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


def weighted_choice(values: list[tuple[str, int]]) -> str:
    labels = [label for label, _ in values]
    weights = [weight for _, weight in values]
    return random.choices(labels, weights=weights, k=1)[0]


def generate_users(count: int = USER_COUNT) -> list[dict[str, object]]:
    users: list[dict[str, object]] = []
    base_time = datetime.now(UTC) - timedelta(days=180)
    for index in range(1, count + 1):
        user_id = f"user_{index:03d}" if index <= 999 else f"user_{index:04d}"
        city = weighted_choice(CITY_WEIGHTS)
        interests = random.sample(INTEREST_POOL, k=3)
        created_at = base_time + timedelta(minutes=index * 45 + random.randint(0, 120))
        users.append(
            {
                "_id": user_id,
                "username": user_id,
                "display_name": f"User {index:03d}" if index <= 999 else f"User {index:04d}",
                "city": city,
                "interests": interests,
                "created_at": created_at.isoformat(),
            }
        )
    return users


def main() -> None:
    random.seed(SEED)
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    users = generate_users()
    with USERS_FILE.open("w", encoding="utf-8") as handle:
        json.dump(users, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"Wrote {len(users)} users to {USERS_FILE}")


if __name__ == "__main__":
    main()
