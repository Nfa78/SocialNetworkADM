from enum import StrEnum


class ContentType(StrEnum):
    POST = "post"
    REVIEW = "review"
    COMMENT = "comment"


class PostStyle(StrEnum):
    FOOD = "food"
    CULTURE = "culture"
    TRAVEL = "travel"
    LIFESTYLE = "lifestyle"
    EVENT = "event"
    GUIDE = "guide"


class RelationshipType(StrEnum):
    LIKE = "like"
    FOLLOW = "follow"


class RelationshipTargetType(StrEnum):
    USER = "user"
    VENUE = "venue"
    CONTENT = "content"


class InteractionType(StrEnum):
    VIEW = "view"


class InteractionSource(StrEnum):
    FEED = "feed"
    PROFILE = "profile"
    SEARCH = "search"
    VENUE = "venue"
    RECOMMENDATION = "recommendation"
    DIRECT = "direct"
    UNKNOWN = "unknown"


class ActivityEventType(StrEnum):
    CONTENT_CREATED = "content_created"
    REVIEW_CREATED = "review_created"
    COMMENT_CREATED = "comment_created"
    LIKE_CREATED = "like_created"
    LIKE_REMOVED = "like_removed"
    FOLLOW_CREATED = "follow_created"
    FOLLOW_REMOVED = "follow_removed"
    CHECKIN_CREATED = "checkin_created"
    VIEW_CREATED = "view_created"
    SHARE_CREATED = "share_created"


class ProjectionStatus(StrEnum):
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
