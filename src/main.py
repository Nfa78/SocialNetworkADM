from typing import Annotated

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import Field

from src.bootstrap import bootstrap
from src.db import close_connections, mongo_db, neo4j_session
from src.domain.models import ActivityEventCreate, ContentCreate, InteractionCreate, RelationshipCreate, UserCreate
from src.services.activity_service import ActivityService
from src.services.content_service import ContentService
from src.services.interaction_service import InteractionService
from src.services.relationship_service import RelationshipService
from src.services.user_service import UserService

app = FastAPI(title="Social Network Analytics Platform")


@app.on_event("shutdown")
def shutdown() -> None:
    close_connections()


@app.get("/health")
def health() -> dict[str, object]:
    mongo_db.command("ping")
    with neo4j_session() as session:
        neo4j_result = session.run("RETURN 1 AS ok").single()
    return {"status": "ok", "mongodb": "ok", "neo4j": neo4j_result["ok"]}


@app.post("/bootstrap")
def run_bootstrap() -> dict[str, object]:
    return bootstrap()


@app.post("/users")
def create_user(user: UserCreate) -> dict[str, object]:
    service = UserService()
    created_user = service.upsert_user(user)
    return jsonable_encoder(created_user)


@app.get("/users/{user_id}")
def get_user(user_id: str) -> dict[str, object]:
    service = UserService()
    user = service.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return jsonable_encoder(user)


@app.post("/content")
def create_content(content: Annotated[ContentCreate, Field(discriminator="type")]) -> dict[str, object]:
    service = ContentService()
    created_content = service.create_content(content)
    return jsonable_encoder(created_content)


@app.get("/content/{content_id}")
def get_content(content_id: str) -> dict[str, object]:
    service = ContentService()
    content = service.get_content(content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return jsonable_encoder(content)


@app.post("/activity-events")
def create_activity_event(activity_event: ActivityEventCreate) -> dict[str, object]:
    service = ActivityService()
    created_activity_event = service.create_activity_event(activity_event)
    return jsonable_encoder(created_activity_event)


@app.post("/relationships")
def create_relationship(relationship: RelationshipCreate) -> dict[str, object]:
    service = RelationshipService()
    created_relationship = service.create_relationship(relationship)
    return jsonable_encoder(created_relationship)


@app.post("/interactions")
def create_interaction(interaction: InteractionCreate) -> dict[str, object]:
    service = InteractionService()
    created_interaction = service.create_interaction(interaction)
    return jsonable_encoder(created_interaction)


@app.get("/relationships/{relationship_id}")
def get_relationship(relationship_id: str) -> dict[str, object]:
    service = RelationshipService()
    relationship = service.get_relationship(relationship_id)
    if relationship is None:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return jsonable_encoder(relationship)


@app.delete("/relationships/{relationship_id}")
def delete_relationship(relationship_id: str) -> dict[str, object]:
    service = RelationshipService()
    deleted = service.delete_relationship(relationship_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return {"deleted": True}
