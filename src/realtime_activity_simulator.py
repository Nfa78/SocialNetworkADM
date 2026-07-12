import json
import logging
import os
import random
import time
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from pymongo import MongoClient
from pymongo.database import Database

from src.settings import settings


logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("SIMULATOR_API_BASE_URL", "http://app:8000").rstrip("/")
INTERVAL_SECONDS = float(os.getenv("SIMULATOR_INTERVAL_SECONDS", "3"))
RECENT_SAMPLE_LIMIT = int(os.getenv("SIMULATOR_RECENT_SAMPLE_LIMIT", "300"))

CITIES = ["Rome", "Milan", "Naples", "Florence", "Bologna", "Turin", "Palermo"]
INTERESTS = ["food", "culture", "travel", "restaurants", "museums", "coffee", "street-food", "events"]
POST_STYLES = ["food", "culture", "travel", "lifestyle", "event", "guide"]
CATEGORIES = ["restaurant", "museum", "cafe", "festival", "gallery", "market", "local-guide"]
HASHTAGS = ["food", "culture", "rome", "hiddenplaces", "review", "weekend", "local", "gastronomy"]
INTERACTION_SOURCES = ["feed", "profile", "search", "venue", "recommendation", "direct"]


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def get(self, path: str) -> dict[str, Any]:
        return self._request("GET", path)

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", path, payload)

    def delete(self, path: str) -> dict[str, Any]:
        return self._request("DELETE", path)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )

        with urlopen(request, timeout=10) as response:
            body = response.read()
            if not body:
                return {}
            return json.loads(body.decode("utf-8"))


class RealtimeActivitySimulator:
    def __init__(self, api: ApiClient, mongo_db: Database) -> None:
        self.api = api
        self.mongo_db = mongo_db

    def run_forever(self) -> None:
        logger.info("Starting realtime simulator with interval=%ss api=%s", INTERVAL_SECONDS, API_BASE_URL)
        self.wait_for_api()
        self.ensure_initial_user()

        while True:
            self.run_one_action()
            time.sleep(INTERVAL_SECONDS)

    def wait_for_api(self) -> None:
        while True:
            try:
                health = self.api.get("/health")
                logger.info("API is ready: %s", health)
                return
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                logger.info("Waiting for API at %s: %s", API_BASE_URL, exc)
                time.sleep(3)

    def run_one_action(self) -> None:
        action = self.choose_action()
        try:
            label = action()
            logger.info("simulated_event=%s at=%s", label, datetime.now(UTC).isoformat())
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            logger.warning("Simulator action failed: %s", exc)

    def choose_action(self) -> Any:
        actions = [
            (self.create_user, 10),
            (self.create_content, 25),
            (self.create_like, 18),
            (self.create_follow, 16),
            (self.remove_like, 8),
            (self.remove_follow, 8),
            (self.create_view, 15),
        ]
        return random.choices([action for action, _ in actions], weights=[weight for _, weight in actions], k=1)[0]

    def ensure_initial_user(self) -> dict[str, Any]:
        user = self.sample_user()
        if user is not None:
            return user
        self.create_user()
        user = self.sample_user()
        if user is None:
            raise RuntimeError("Simulator could not create an initial user")
        return user

    def create_user(self) -> str:
        suffix = uuid4().hex[:8]
        payload = {
            "username": f"sim_user_{suffix}",
            "display_name": f"Sim User {suffix}",
            "city": random.choice(CITIES),
            "interests": random.sample(INTERESTS, k=random.randint(2, 4)),
        }
        created_user = self.api.post("/users", payload)
        return f"user_created:{self.document_id(created_user)}"

    def create_content(self) -> str:
        user = self.ensure_initial_user()
        content_type = self.choose_content_type()

        if content_type == "review":
            payload = self.build_review_payload(user)
        elif content_type == "comment":
            payload = self.build_comment_payload(user)
        else:
            payload = self.build_post_payload(user)

        created_content = self.api.post("/content", payload)
        return f"{content_type}_created:{self.document_id(created_content)}"

    def create_like(self) -> str:
        user = self.ensure_initial_user()
        content = self.ensure_content()
        payload = {
            "type": "like",
            "source_user_id": self.document_id(user),
            "target_type": "content",
            "target_id": self.document_id(content),
        }
        created_relationship = self.api.post("/relationships", payload)
        return f"like_created:{self.document_id(created_relationship)}"

    def create_follow(self) -> str:
        user = self.ensure_initial_user()
        target_type, target_id = self.choose_follow_target(self.document_id(user))
        payload = {
            "type": "follow",
            "source_user_id": self.document_id(user),
            "target_type": target_type,
            "target_id": target_id,
        }
        created_relationship = self.api.post("/relationships", payload)
        return f"follow_created:{self.document_id(created_relationship)}"

    def remove_like(self) -> str:
        relationship = self.sample_relationship({"type": "like"})
        if relationship is None:
            return self.create_like()
        self.api.delete(f"/relationships/{self.document_id(relationship)}")
        return f"like_removed:{self.document_id(relationship)}"

    def remove_follow(self) -> str:
        relationship = self.sample_relationship({"type": "follow"})
        if relationship is None:
            return self.create_follow()
        self.api.delete(f"/relationships/{self.document_id(relationship)}")
        return f"follow_removed:{self.document_id(relationship)}"

    def create_view(self) -> str:
        user = self.ensure_initial_user()
        content = self.ensure_content()
        payload = {
            "type": "view",
            "user_id": self.document_id(user),
            "content_id": self.document_id(content),
            "source": random.choice(INTERACTION_SOURCES),
            "session_id": f"sim_session_{uuid4().hex[:10]}",
            "duration_ms": random.randint(800, 45000),
        }
        created_interaction = self.api.post("/interactions", payload)
        return f"view_created:{self.document_id(created_interaction)}"

    def choose_content_type(self) -> str:
        choices = ["post"]
        weights = [60]

        if self.sample_venue() is not None:
            choices.append("review")
            weights.append(20)

        if self.sample_content() is not None:
            choices.append("comment")
            weights.append(20)

        return random.choices(choices, weights=weights, k=1)[0]

    def build_post_payload(self, user: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": "post",
            "author_id": self.document_id(user),
            "text": random.choice(
                [
                    "Found a great local food spot worth sharing.",
                    "Small cultural stop with a lot of character.",
                    "Weekend guide for a relaxed city walk.",
                    "A quick note from today's food and culture route.",
                ]
            ),
            "style": random.choice(POST_STYLES),
            "category": random.choice(CATEGORIES),
            "hashtags": random.sample(HASHTAGS, k=random.randint(2, 4)),
            "source": "realtime_simulator",
            "sentiment": self.random_sentiment(),
        }

        venue = self.sample_venue()
        if venue is not None and random.random() < 0.6:
            payload["venue_id"] = self.document_id(venue)
            payload["location"] = venue.get("city")

        return payload

    def build_review_payload(self, user: dict[str, Any]) -> dict[str, Any]:
        venue = self.sample_venue()
        if venue is None:
            return self.build_post_payload(user)

        return {
            "type": "review",
            "author_id": self.document_id(user),
            "venue_id": self.document_id(venue),
            "text": random.choice(
                [
                    "Fresh visit: strong atmosphere and good service.",
                    "Tried this place today and would recommend it.",
                    "Useful stop for gastronomy and local discovery.",
                    "Solid experience with a few memorable details.",
                ]
            ),
            "rating": random.randint(3, 5),
            "hashtags": random.sample(HASHTAGS, k=random.randint(2, 4)),
            "location": venue.get("city"),
            "source": "realtime_simulator",
            "sentiment": self.random_sentiment(),
        }

    def build_comment_payload(self, user: dict[str, Any]) -> dict[str, Any]:
        parent_content = self.sample_content()
        if parent_content is None:
            return self.build_post_payload(user)

        return {
            "type": "comment",
            "author_id": self.document_id(user),
            "parent_content_id": self.document_id(parent_content),
            "text": random.choice(
                [
                    "Adding this to my saved ideas.",
                    "This matches what I saw recently too.",
                    "Good tip, especially for a short visit.",
                    "I would pair this with another nearby stop.",
                ]
            ),
            "hashtags": random.sample(HASHTAGS, k=random.randint(1, 3)),
            "source": "realtime_simulator",
            "sentiment": self.random_sentiment(),
        }

    def choose_follow_target(self, source_user_id: str) -> tuple[str, str]:
        if random.random() < 0.5:
            target_user = self.sample_user({"_id": {"$ne": source_user_id}})
            if target_user is not None:
                return "user", self.document_id(target_user)

        venue = self.sample_venue()
        if venue is not None:
            return "venue", self.document_id(venue)

        target_user = self.sample_user({"_id": {"$ne": source_user_id}})
        if target_user is None:
            self.create_user()
            target_user = self.sample_user({"_id": {"$ne": source_user_id}})
        if target_user is None:
            raise ValueError("No valid follow target is available")
        return "user", self.document_id(target_user)

    def ensure_content(self) -> dict[str, Any]:
        content = self.sample_content()
        if content is not None:
            return content
        self.create_content()
        content = self.sample_content()
        if content is None:
            raise RuntimeError("Simulator could not create initial content")
        return content

    def sample_user(self, query: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return self.sample_document("users", query)

    def sample_content(self, query: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return self.sample_document("content", query)

    def sample_venue(self, query: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return self.sample_document("venues", query)

    def sample_relationship(self, query: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return self.sample_document("relationships", query)

    def sample_document(self, collection_name: str, query: dict[str, Any] | None = None) -> dict[str, Any] | None:
        documents = list(
            self.mongo_db[collection_name]
            .find(query or {})
            .sort("created_at", -1)
            .limit(RECENT_SAMPLE_LIMIT)
        )
        if not documents:
            return None
        return random.choice(documents)

    def random_sentiment(self) -> dict[str, Any]:
        label = random.choice(["negative", "neutral", "positive", "positive", "positive"])
        score = round(random.uniform(0.55, 0.98), 2)
        polarity = {"negative": 0, "neutral": 2, "positive": 4}[label]
        return {"label": label, "score": score, "polarity": polarity}

    def document_id(self, document: dict[str, Any]) -> str:
        document_id = document.get("_id", document.get("id"))
        if document_id is None:
            raise ValueError(f"Document does not contain an id: {document}")
        return str(document_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    mongo_client = MongoClient(settings.mongo_uri)

    try:
        simulator = RealtimeActivitySimulator(
            api=ApiClient(API_BASE_URL),
            mongo_db=mongo_client[settings.mongo_database],
        )
        simulator.run_forever()
    except KeyboardInterrupt:
        logger.info("Stopping realtime simulator")
    finally:
        mongo_client.close()


if __name__ == "__main__":
    main()
