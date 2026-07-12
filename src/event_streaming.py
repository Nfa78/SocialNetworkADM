import json
import logging
from datetime import datetime
from typing import Any

from src.domain.models import ActivityEventDocument
from src.settings import settings


logger = logging.getLogger(__name__)


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(_enum_value(value))


def build_activity_event_envelope(activity_event: ActivityEventDocument) -> dict[str, Any]:
    return {
        "event_id": activity_event.id,
        "event_type": _enum_value(activity_event.type),
        "occurred_at": activity_event.created_at.isoformat(),
        "actor_user_id": activity_event.actor_user_id,
        "target_type": _enum_value(activity_event.target_type),
        "target_id": activity_event.target_id,
        "source_service": settings.kafka_source_service,
        "payload": activity_event.metadata,
    }


class KafkaActivityEventProducer:
    def __init__(
        self,
        bootstrap_servers: str | None = None,
        topic: str | None = None,
        enabled: bool | None = None,
        client_id: str | None = None,
    ) -> None:
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.topic = topic or settings.kafka_activity_topic
        self.enabled = settings.kafka_enabled if enabled is None else enabled
        self.client_id = client_id or settings.kafka_source_service
        self._producer: Any | None = None

        if not self.enabled:
            return

        try:
            from confluent_kafka import Producer
        except ImportError:
            logger.warning("Kafka publishing is enabled, but confluent-kafka is not installed")
            self.enabled = False
            return

        self._producer = Producer(
            {
                "bootstrap.servers": self.bootstrap_servers,
                "client.id": self.client_id,
                "message.timeout.ms": 5000,
                "socket.timeout.ms": 2000,
            }
        )

    def publish_activity_event(self, activity_event: ActivityEventDocument) -> bool:
        if not self.enabled or self._producer is None:
            return False

        envelope = build_activity_event_envelope(activity_event)
        value = json.dumps(envelope, default=_json_default, separators=(",", ":")).encode("utf-8")

        try:
            self._producer.produce(
                self.topic,
                key=activity_event.id.encode("utf-8"),
                value=value,
                on_delivery=self._delivery_report,
            )
            self._producer.poll(0)
            return True
        except BufferError:
            self._producer.poll(1)
            logger.exception("Kafka producer queue is full while publishing activity event %s", activity_event.id)
        except Exception:
            logger.exception("Failed to publish activity event %s to Kafka", activity_event.id)

        return False

    def flush(self, timeout: float = 5.0) -> None:
        if self._producer is not None:
            self._producer.flush(timeout)

    def _delivery_report(self, error: Any, message: Any) -> None:
        if error is not None:
            logger.warning("Kafka delivery failed for activity event: %s", error)
            return
        logger.debug(
            "Published activity event to Kafka topic=%s partition=%s offset=%s",
            message.topic(),
            message.partition(),
            message.offset(),
        )


_activity_event_producer: KafkaActivityEventProducer | None = None


def get_activity_event_producer() -> KafkaActivityEventProducer:
    global _activity_event_producer
    if _activity_event_producer is None:
        _activity_event_producer = KafkaActivityEventProducer()
    return _activity_event_producer


def close_activity_event_producer() -> None:
    if _activity_event_producer is not None:
        _activity_event_producer.flush()
