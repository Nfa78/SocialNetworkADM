from src.db import mongo_db, neo4j_session
from src.mongo_schema import initialize_mongodb_collections
from src.neo4j_schema import initialize_neo4j_indexes


def check_mongodb() -> dict[str, str]:
    mongo_db.command("ping")
    return {"status": "ready"}


def check_neo4j() -> dict[str, str]:
    with neo4j_session() as session:
        session.run("RETURN 1")
    return {"status": "ready"}


def bootstrap() -> dict[str, object]:
    return {
        "status": "initialized",
        "mongodb": check_mongodb(),
        "neo4j": check_neo4j(),
        "collections": initialize_mongodb_collections(),
        "neo4j_indexes": initialize_neo4j_indexes(),
    }
