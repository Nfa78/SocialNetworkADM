from src.db import neo4j_session
from src.domain.models import UserDocument


class Neo4jUserRepository:
    def project_user(self, user: UserDocument) -> None:
        with neo4j_session() as session:
            session.run(
                """
                MERGE (u:User {id: $user_id})
                SET u.username = $username,
                    u.display_name = $display_name,
                    u.city = $city
                """,
                user_id=user.id,
                username=user.username,
                display_name=user.display_name,
                city=user.city,
            )
