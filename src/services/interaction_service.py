from src.domain.models import EmbeddedUserInteraction, InteractionCreate, InteractionDocument
from src.repositories.mongo_repository import ContentRepository, InteractionRepository, UserRepository


class InteractionService:
    def __init__(
        self,
        interaction_repository: InteractionRepository | None = None,
        user_repository: UserRepository | None = None,
        content_repository: ContentRepository | None = None,
    ) -> None:
        self.interaction_repository = interaction_repository or InteractionRepository()
        self.user_repository = user_repository or UserRepository()
        self.content_repository = content_repository or ContentRepository()

    def create_interaction(self, interaction: InteractionCreate) -> InteractionDocument:
        interaction_document = InteractionDocument.from_create(interaction)
        created_interaction = self.interaction_repository.create(interaction_document)
        self.content_repository.increment_interaction_counter(created_interaction)

        if created_interaction.user_id is not None:
            self.user_repository.push_recent_interaction(
                created_interaction.user_id,
                EmbeddedUserInteraction.from_interaction(created_interaction),
            )

        return created_interaction
