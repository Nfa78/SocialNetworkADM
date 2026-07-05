from datetime import UTC, datetime

from src.domain.enums import ActivityEventType, ProjectionStatus, RelationshipType
from src.domain.models import ActivityEventCreate, RelationshipCreate, RelationshipDocument
from src.repositories.mongo_repository import RelationshipRepository
from src.repositories.neo4j_repository import Neo4jRepository
from src.services.activity_service import ActivityService


class RelationshipService:
    def __init__(
        self,
        relationship_repository: RelationshipRepository | None = None,
        graph_repository: Neo4jRepository | None = None,
        activity_service: ActivityService | None = None,
    ) -> None:
        self.relationship_repository = relationship_repository or RelationshipRepository()
        self.graph_repository = graph_repository or Neo4jRepository()
        self.activity_service = activity_service or ActivityService()

    def create_relationship(self, relationship: RelationshipCreate) -> RelationshipDocument:
        relationship_document = RelationshipDocument.from_create(relationship)
        created_relationship = self.relationship_repository.create(relationship_document)
        try:
            self.graph_repository.project_relationship(created_relationship)
        except Exception as exc:
            self.relationship_repository.mark_projection_failed(created_relationship.id, str(exc))
            raise

        projected_at = datetime.now(UTC)
        self.relationship_repository.mark_projection_synced(created_relationship.id, projected_at)
        created_relationship.projection_status = ProjectionStatus.SYNCED
        created_relationship.projected_at = projected_at
        created_relationship.projection_error = None
        self.activity_service.create_activity_event(
            ActivityEventCreate(
                type=self._activity_type_for_created_relationship(created_relationship),
                actor_user_id=created_relationship.source_user_id,
                target_type=created_relationship.target_type,
                target_id=created_relationship.target_id,
                metadata={"relationship_id": created_relationship.id},
            )
        )
        return created_relationship

    def get_relationship(self, relationship_id: str) -> RelationshipDocument | None:
        stored_relationship = self.relationship_repository.find_by_id(relationship_id)
        if stored_relationship is None:
            return None
        return RelationshipDocument.model_validate(stored_relationship)

    def delete_relationship(self, relationship_id: str) -> bool:
        stored_relationship = self.relationship_repository.find_by_id(relationship_id)
        if stored_relationship is None:
            return False

        relationship = RelationshipDocument.model_validate(stored_relationship)
        self.graph_repository.delete_relationship(relationship)
        deleted = self.relationship_repository.delete_by_id(relationship_id)
        if deleted:
            self.activity_service.create_activity_event(
                ActivityEventCreate(
                    type=self._activity_type_for_removed_relationship(relationship),
                    actor_user_id=relationship.source_user_id,
                    target_type=relationship.target_type,
                    target_id=relationship.target_id,
                    metadata={"relationship_id": relationship.id},
                )
            )
        return deleted

    def _activity_type_for_created_relationship(self, relationship: RelationshipDocument) -> ActivityEventType:
        if relationship.type == RelationshipType.LIKE:
            return ActivityEventType.LIKE_CREATED
        return ActivityEventType.FOLLOW_CREATED

    def _activity_type_for_removed_relationship(self, relationship: RelationshipDocument) -> ActivityEventType:
        if relationship.type == RelationshipType.LIKE:
            return ActivityEventType.LIKE_REMOVED
        return ActivityEventType.FOLLOW_REMOVED
