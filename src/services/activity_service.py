from src.domain.models import ActivityEventCreate, ActivityEventDocument
from src.repositories.mongo_repository import ActivityEventRepository


class ActivityService:
    def __init__(self, activity_event_repository: ActivityEventRepository | None = None) -> None:
        self.activity_event_repository = activity_event_repository or ActivityEventRepository()

    def create_activity_event(self, activity_event: ActivityEventCreate) -> ActivityEventDocument:
        activity_event_document = ActivityEventDocument.from_create(activity_event)
        return self.activity_event_repository.create(activity_event_document)
