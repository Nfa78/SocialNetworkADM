import json
import logging
from datetime import UTC, datetime
from typing import Any

from src.db import close_connections, mongo_db
from src.settings import settings


logger = logging.getLogger(__name__)
CONSUMPTION_LOG_COLLECTION = "activity_event_consumption_log"


def build_consumer() -> Any:
    try:
        from confluent_kafka import Consumer
    except ImportError as exc:
        raise RuntimeError("confluent-kafka is required to run the Kafka demo consumer") from exc

    return Consumer(
        {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": "social-analytics-activity-demo",
            "client.id": "social-analytics-activity-consumer",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )


def decode_message(message: Any) -> dict[str, Any]:
    raw_value = message.value()
    if raw_value is None:
        return {}
    return json.loads(raw_value.decode("utf-8"))


def store_consumed_event(event: dict[str, Any], message: Any) -> None:
    consumed_at = datetime.now(UTC)
    event_id = event.get("event_id")
    record_id = event_id or f"{message.topic()}-{message.partition()}-{message.offset()}"

    mongo_db[CONSUMPTION_LOG_COLLECTION].update_one(
        {"_id": record_id},
        {
            "$set": {
                "event": event,
                "topic": message.topic(),
                "partition": message.partition(),
                "offset": message.offset(),
                "consumed_at": consumed_at,
            },
            "$setOnInsert": {"first_consumed_at": consumed_at},
        },
        upsert=True,
    )


def consume_forever() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    consumer = build_consumer()
    consumer.subscribe([settings.kafka_activity_topic])
    logger.info("Consuming Kafka topic %s from %s", settings.kafka_activity_topic, settings.kafka_bootstrap_servers)

    try:
        while True:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                logger.warning("Kafka consumer error: %s", message.error())
                continue

            event = decode_message(message)
            store_consumed_event(event, message)
            logger.info(
                "Consumed activity event event_id=%s event_type=%s offset=%s",
                event.get("event_id"),
                event.get("event_type"),
                message.offset(),
            )
    except KeyboardInterrupt:
        logger.info("Stopping Kafka activity consumer")
    finally:
        consumer.close()
        close_connections()


if __name__ == "__main__":
    consume_forever()
