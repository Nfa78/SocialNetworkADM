from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

from src.domain.enums import (
    ActivityEventType,
    ContentType,
    InteractionSource,
    InteractionType,
    PostStyle,
    ProjectionStatus,
    RelationshipTargetType,
    RelationshipType,
)


def new_document_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class MongoDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    id: str = Field(alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_mongo(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="python", exclude_none=True)


class DomainModel(BaseModel):
    model_config = ConfigDict(use_enum_values=True)


class VenueDocument(MongoDocument):
    id: str = Field(default_factory=lambda: new_document_id("venue"), alias="_id")
    name: str
    domain: Literal["gastronomy", "cultural"]
    category: str
    city: str


class UserCreate(DomainModel):
    id: str | None = Field(default=None, alias="_id")
    username: str
    display_name: str | None = None
    city: str | None = None
    interests: list[str] = Field(default_factory=list)
    recent_interactions: list["EmbeddedUserInteraction"] = Field(default_factory=list)
    created_at: datetime | None = None


class ContentMetrics(DomainModel):
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    last_viewed_at: datetime | None = None


class SentimentMetadata(DomainModel):
    label: Literal["negative", "neutral", "positive"]
    score: float | None = None
    polarity: int | None = None


class ContentCoordinates(DomainModel):
    latitude: float
    longitude: float

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, latitude: float) -> float:
        if latitude < -90 or latitude > 90:
            raise ValueError("latitude must be between -90 and 90")
        return latitude

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, longitude: float) -> float:
        if longitude < -180 or longitude > 180:
            raise ValueError("longitude must be between -180 and 180")
        return longitude


class ContentLocation(DomainModel):
    label: str | None = None
    coordinates: ContentCoordinates | None = None

    @model_validator(mode="after")
    def validate_location_value(self) -> "ContentLocation":
        if self.label is None and self.coordinates is None:
            raise ValueError("location requires either label or coordinates")
        return self


class PostContentCreate(DomainModel):
    id: str | None = Field(default=None, alias="_id")
    type: Literal["post"] = ContentType.POST
    author_id: str
    text: str
    style: PostStyle | None = None
    category: str | None = None
    venue_id: str | None = None
    hashtags: list[str] = Field(default_factory=list)
    location: str | ContentLocation | None = None
    source: str | None = None
    external_id: str | None = None
    sentiment: SentimentMetadata | None = None
    created_at: datetime | None = None


class ReviewContentCreate(DomainModel):
    id: str | None = Field(default=None, alias="_id")
    type: Literal["review"] = ContentType.REVIEW
    author_id: str
    venue_id: str
    text: str
    rating: int | float
    hashtags: list[str] = Field(default_factory=list)
    location: str | ContentLocation | None = None
    source: str | None = None
    external_id: str | None = None
    sentiment: SentimentMetadata | None = None
    created_at: datetime | None = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, rating: int | float) -> int | float:
        if rating < 1 or rating > 5:
            raise ValueError("rating must be between 1 and 5")
        return rating


class CommentContentCreate(DomainModel):
    id: str | None = Field(default=None, alias="_id")
    type: Literal["comment"] = ContentType.COMMENT
    author_id: str
    parent_content_id: str
    text: str
    hashtags: list[str] = Field(default_factory=list)
    location: str | ContentLocation | None = None
    source: str | None = None
    external_id: str | None = None
    sentiment: SentimentMetadata | None = None
    created_at: datetime | None = None


ContentCreate = PostContentCreate | ReviewContentCreate | CommentContentCreate


class PostContentDocument(PostContentCreate, MongoDocument):
    id: str = Field(default_factory=lambda: new_document_id("content"), alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metrics: ContentMetrics = Field(default_factory=ContentMetrics)


class ReviewContentDocument(ReviewContentCreate, MongoDocument):
    id: str = Field(default_factory=lambda: new_document_id("content"), alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metrics: ContentMetrics = Field(default_factory=ContentMetrics)


class CommentContentDocument(CommentContentCreate, MongoDocument):
    id: str = Field(default_factory=lambda: new_document_id("content"), alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metrics: ContentMetrics = Field(default_factory=ContentMetrics)


ContentDocument = PostContentDocument | ReviewContentDocument | CommentContentDocument
content_document_adapter = TypeAdapter(ContentDocument)


def content_document_from_create(content: ContentCreate) -> ContentDocument:
    content_data = content.model_dump(exclude_none=True)
    if content.type == ContentType.POST:
        return PostContentDocument(**content_data)
    if content.type == ContentType.REVIEW:
        return ReviewContentDocument(**content_data)
    if content.type == ContentType.COMMENT:
        return CommentContentDocument(**content_data)
    raise ValueError(f"Unsupported content type: {content.type}")


class RelationshipCreate(DomainModel):
    type: RelationshipType
    source_user_id: str
    target_type: RelationshipTargetType
    target_id: str
    created_at: datetime | None = None

    @model_validator(mode="after")
    def validate_relationship_target(self) -> "RelationshipCreate":
        if self.type == RelationshipType.LIKE and self.target_type != RelationshipTargetType.CONTENT:
            raise ValueError("like relationships must target content")
        if self.type == RelationshipType.FOLLOW and self.target_type == RelationshipTargetType.CONTENT:
            raise ValueError("follow relationships must target users or venues")
        return self


class RelationshipDocument(MongoDocument):
    id: str = Field(default_factory=lambda: new_document_id("relationship"), alias="_id")
    type: RelationshipType
    source_user_id: str
    target_type: RelationshipTargetType
    target_id: str
    projection_status: ProjectionStatus = ProjectionStatus.PENDING
    projected_at: datetime | None = None
    projection_error: str | None = None

    @classmethod
    def from_create(cls, relationship: RelationshipCreate) -> "RelationshipDocument":
        return cls(**relationship.model_dump())


class InteractionCreate(DomainModel):
    type: InteractionType
    content_id: str
    user_id: str | None = None
    source: InteractionSource = InteractionSource.UNKNOWN
    session_id: str | None = None
    duration_ms: int | None = None
    created_at: datetime | None = None

    @field_validator("duration_ms")
    @classmethod
    def validate_duration_ms(cls, duration_ms: int | None) -> int | None:
        if duration_ms is not None and duration_ms < 0:
            raise ValueError("duration_ms must be greater than or equal to 0")
        return duration_ms


class InteractionDocument(MongoDocument):
    id: str = Field(default_factory=lambda: new_document_id("interaction"), alias="_id")
    type: InteractionType
    content_id: str
    user_id: str | None = None
    source: InteractionSource = InteractionSource.UNKNOWN
    session_id: str | None = None
    duration_ms: int | None = None

    @classmethod
    def from_create(cls, interaction: InteractionCreate) -> "InteractionDocument":
        return cls(**interaction.model_dump())


class EmbeddedUserInteraction(DomainModel):
    type: InteractionType
    content_id: str
    created_at: datetime
    source: InteractionSource = InteractionSource.UNKNOWN
    session_id: str | None = None
    duration_ms: int | None = None

    @classmethod
    def from_interaction(cls, interaction: InteractionDocument) -> "EmbeddedUserInteraction":
        return cls(
            type=interaction.type,
            content_id=interaction.content_id,
            created_at=interaction.created_at,
            source=interaction.source,
            session_id=interaction.session_id,
            duration_ms=interaction.duration_ms,
        )


class UserDocument(MongoDocument):
    id: str = Field(default_factory=lambda: new_document_id("user"), alias="_id")
    username: str
    display_name: str | None = None
    city: str | None = None
    interests: list[str] = Field(default_factory=list)
    recent_interactions: list[EmbeddedUserInteraction] = Field(default_factory=list, max_length=50)

    @classmethod
    def from_create(cls, user: UserCreate) -> "UserDocument":
        user_data = user.model_dump(by_alias=True, mode="python", exclude_none=True)
        if "_id" not in user_data:
            user_data["_id"] = new_document_id("user")
        return cls(**user_data)


class ActivityEventCreate(DomainModel):
    type: ActivityEventType
    actor_user_id: str
    target_type: RelationshipTargetType
    target_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActivityEventDocument(ActivityEventCreate, MongoDocument):
    id: str = Field(default_factory=lambda: new_document_id("activity"), alias="_id")

    @classmethod
    def from_create(cls, activity_event: ActivityEventCreate) -> "ActivityEventDocument":
        return cls(**activity_event.model_dump())
