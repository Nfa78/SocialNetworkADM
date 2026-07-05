from src.domain.models import UserCreate, UserDocument
from src.repositories.mongo_repository import UserRepository
from src.repositories.neo4j_user_repository import Neo4jUserRepository


class UserService:
    def __init__(
        self,
        user_repository: UserRepository | None = None,
        graph_repository: Neo4jUserRepository | None = None,
    ) -> None:
        self.user_repository = user_repository or UserRepository()
        self.graph_repository = graph_repository or Neo4jUserRepository()

    def upsert_user(self, user: UserCreate) -> UserDocument:
        user_document = UserDocument.from_create(user)
        stored_user = self.user_repository.upsert(user_document)
        self.graph_repository.project_user(stored_user)
        return stored_user

    def get_user(self, user_id: str) -> UserDocument | None:
        stored_user = self.user_repository.find_by_id(user_id)
        if stored_user is None:
            return None
        return UserDocument.model_validate(stored_user)
