from typing import Any
from datetime import UTC, datetime

from pymongo.collection import Collection

from src.db import mongo_db
from src.domain.enums import InteractionType, ProjectionStatus
from src.domain.models import (
    ActivityEventDocument,
    ContentDocument,
    EmbeddedUserInteraction,
    InteractionDocument,
    RelationshipDocument,
    UserDocument,
    content_document_adapter,
)


class MongoRepository:
    def __init__(self, collection_name: str) -> None:
        self.collection: Collection = mongo_db[collection_name]

    def insert_one(self, document: dict[str, Any]) -> dict[str, Any]:
        self.collection.insert_one(document)
        return document

    def find_by_id(self, document_id: str) -> dict[str, Any] | None:
        return self.collection.find_one({"_id": document_id})

    def delete_by_id(self, document_id: str) -> bool:
        result = self.collection.delete_one({"_id": document_id})
        return result.deleted_count == 1

    def update_by_id(self, document_id: str, changes: dict[str, Any]) -> bool:
        result = self.collection.update_one({"_id": document_id}, {"$set": changes})
        return result.modified_count == 1


class RelationshipRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("relationships")

    def create(self, relationship: RelationshipDocument) -> RelationshipDocument:
        self.insert_one(relationship.to_mongo())
        return relationship

    def mark_projection_synced(self, relationship_id: str, projected_at: datetime | None = None) -> bool:
        projected_at = projected_at or datetime.now(UTC)
        return self.update_by_id(
            relationship_id,
            {
                "projection_status": ProjectionStatus.SYNCED.value,
                "projected_at": projected_at,
                "projection_error": None,
            },
        )

    def mark_projection_failed(self, relationship_id: str, error: str) -> bool:
        return self.update_by_id(
            relationship_id,
            {
                "projection_status": ProjectionStatus.FAILED.value,
                "projection_error": error,
            },
        )


class InteractionRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("interactions")

    def create(self, interaction: InteractionDocument) -> InteractionDocument:
        self.insert_one(interaction.to_mongo())
        return interaction


class ContentRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("content")

    def create(self, content: ContentDocument) -> ContentDocument:
        self.insert_one(content.to_mongo())
        return content

    def get(self, content_id: str) -> ContentDocument | None:
        stored_content = self.find_by_id(content_id)
        if stored_content is None:
            return None
        return content_document_adapter.validate_python(stored_content)

    def increment_interaction_counter(self, interaction: InteractionDocument) -> bool:
        if interaction.type != InteractionType.VIEW:
            return False

        result = self.collection.update_one(
            {"_id": interaction.content_id},
            {
                "$inc": {"metrics.view_count": 1},
                "$set": {"metrics.last_viewed_at": interaction.created_at},
            },
        )
        return result.modified_count == 1


class UserRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("users")

    def create(self, user: UserDocument) -> UserDocument:
        self.insert_one(user.to_mongo())
        return user

    def upsert(self, user: UserDocument) -> UserDocument:
        self.collection.update_one({"_id": user.id}, {"$set": user.to_mongo()}, upsert=True)
        return user

    def push_recent_interaction(
        self,
        user_id: str,
        interaction: EmbeddedUserInteraction,
        limit: int = 50,
    ) -> bool:
        result = self.collection.update_one(
            {"_id": user_id},
            {
                "$push": {
                    "recent_interactions": {
                        "$each": [interaction.model_dump(mode="python", exclude_none=True)],
                        "$position": 0,
                        "$slice": limit,
                    }
                }
            },
        )
        return result.modified_count == 1


class ActivityEventRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("activity_events")

    def create(self, activity_event: ActivityEventDocument) -> ActivityEventDocument:
        self.insert_one(activity_event.to_mongo())
        return activity_event


class VenueRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("venues")

    def upsert(self, venue: dict[str, Any]) -> dict[str, Any]:
        self.collection.update_one(
            {"_id": venue["_id"]},
            {"$set": venue},
            upsert=True,
        )
        return venue
