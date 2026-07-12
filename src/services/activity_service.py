from src.domain.models import ActivityEventCreate, ActivityEventDocument
from src.event_streaming import KafkaActivityEventProducer, get_activity_event_producer
from src.repositories.mongo_repository import ActivityEventRepository


class ActivityService:
    def __init__(
        self,
        activity_event_repository: ActivityEventRepository | None = None,
        activity_event_producer: KafkaActivityEventProducer | None = None,
    ) -> None:
        self.activity_event_repository = activity_event_repository or ActivityEventRepository()
        self.activity_event_producer = activity_event_producer or get_activity_event_producer()

    def create_activity_event(self, activity_event: ActivityEventCreate) -> ActivityEventDocument:
        activity_event_document = ActivityEventDocument.from_create(activity_event)
        created_activity_event = self.activity_event_repository.create(activity_event_document)
        self.activity_event_producer.publish_activity_event(created_activity_event)
        return created_activity_event
