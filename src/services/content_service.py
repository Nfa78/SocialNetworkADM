from src.domain.enums import ActivityEventType, RelationshipTargetType
from src.domain.models import ActivityEventCreate, ContentCreate, ContentDocument, content_document_from_create
from src.repositories.mongo_repository import ContentRepository
from src.repositories.neo4j_repository import Neo4jRepository
from src.services.activity_service import ActivityService


class ContentService:
    def __init__(
        self,
        content_repository: ContentRepository | None = None,
        graph_repository: Neo4jRepository | None = None,
        activity_service: ActivityService | None = None,
    ) -> None:
        self.content_repository = content_repository or ContentRepository()
        self.graph_repository = graph_repository or Neo4jRepository()
        self.activity_service = activity_service or ActivityService()

    def create_content(self, content: ContentCreate) -> ContentDocument:
        content_document = content_document_from_create(content)
        created_content = self.content_repository.create(content_document)
        self.graph_repository.project_content(created_content)
        self.activity_service.create_activity_event(
            ActivityEventCreate(
                type=self._activity_type_for_content(created_content),
                actor_user_id=created_content.author_id,
                target_type=RelationshipTargetType.CONTENT,
                target_id=created_content.id,
                metadata={"content_type": created_content.type},
            )
        )
        return created_content

    def get_content(self, content_id: str) -> ContentDocument | None:
        return self.content_repository.get(content_id)

    def _activity_type_for_content(self, content: ContentDocument) -> ActivityEventType:
        if content.type == "review":
            return ActivityEventType.REVIEW_CREATED
        if content.type == "comment":
            return ActivityEventType.COMMENT_CREATED
        return ActivityEventType.CONTENT_CREATED
