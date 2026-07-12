from src.domain.enums import ActivityEventType, InteractionType, RelationshipTargetType
from src.domain.models import ActivityEventCreate, EmbeddedUserInteraction, InteractionCreate, InteractionDocument
from src.repositories.mongo_repository import ContentRepository, InteractionRepository, UserRepository
from src.repositories.neo4j_repository import Neo4jRepository
from src.services.activity_service import ActivityService


class InteractionService:
    def __init__(
        self,
        interaction_repository: InteractionRepository | None = None,
        user_repository: UserRepository | None = None,
        content_repository: ContentRepository | None = None,
        graph_repository: Neo4jRepository | None = None,
        activity_service: ActivityService | None = None,
    ) -> None:
        self.interaction_repository = interaction_repository or InteractionRepository()
        self.user_repository = user_repository or UserRepository()
        self.content_repository = content_repository or ContentRepository()
        self.graph_repository = graph_repository or Neo4jRepository()
        self.activity_service = activity_service or ActivityService()

    def create_interaction(self, interaction: InteractionCreate) -> InteractionDocument:
        interaction_document = InteractionDocument.from_create(interaction)
        created_interaction = self.interaction_repository.create(interaction_document)
        self.content_repository.increment_interaction_counter(created_interaction)

        if created_interaction.user_id is not None:
            self.user_repository.push_recent_interaction(
                created_interaction.user_id,
                EmbeddedUserInteraction.from_interaction(created_interaction),
            )
            if created_interaction.type == InteractionType.VIEW:
                self.graph_repository.project_viewed_interaction(created_interaction)
            self.activity_service.create_activity_event(
                ActivityEventCreate(
                    type=ActivityEventType.VIEW_CREATED,
                    actor_user_id=created_interaction.user_id,
                    target_type=RelationshipTargetType.CONTENT,
                    target_id=created_interaction.content_id,
                    metadata={
                        "interaction_id": created_interaction.id,
                        "source": created_interaction.source,
                        "session_id": created_interaction.session_id,
                        "duration_ms": created_interaction.duration_ms,
                    },
                )
            )

        return created_interaction
