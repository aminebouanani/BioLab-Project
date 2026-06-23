"""Kafka producer service for fake GLIMS events."""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

from streaming.config import KafkaSettings
from streaming.topics import (
    GLIMS_ORDER_TOPIC,
    GLIMS_PATIENT_TOPIC,
    GLIMS_RESULT_TOPIC,
    GLIMS_SPECIMEN_TOPIC,
    GLIMS_VALIDATION_TOPIC,
)

LOGGER = logging.getLogger(__name__)


class KafkaPublishError(Exception):
    """Raised when Kafka publishing fails."""


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError("Object of type {} is not JSON serializable".format(type(value).__name__))


class KafkaProducerService:
    """Small Kafka producer wrapper that stays optional for local API use."""

    def __init__(self, settings: Optional[KafkaSettings] = None):
        self.settings = settings or KafkaSettings()
        self._producer = None

        if not self.settings.enabled:
            LOGGER.info("Kafka publishing disabled")
            return

        LOGGER.info("Kafka publishing enabled, broker=%s", self.settings.bootstrap_servers)
        try:
            from confluent_kafka import Producer
        except ImportError as exc:
            raise KafkaPublishError(
                "confluent-kafka is required when KAFKA_ENABLED=true. "
                "Install dependencies with 'pip install -r requirements.txt'."
            ) from exc

        self._producer = Producer({"bootstrap.servers": self.settings.bootstrap_servers})

    @property
    def enabled(self):
        return self.settings.enabled

    def route_event_to_topic(self, event):
        event_type = str(event.get("event_type", "")).upper()
        validation_status = str(event.get("validation_status", "")).upper()

        if "PATIENT" in event_type:
            return GLIMS_PATIENT_TOPIC
        if "ORDER" in event_type:
            return GLIMS_ORDER_TOPIC
        if "SPECIMEN" in event_type:
            return GLIMS_SPECIMEN_TOPIC
        if "VALIDATED" in event_type or validation_status == "FINAL":
            return GLIMS_VALIDATION_TOPIC
        if "LAB_RESULT" in event_type or "RESULT" in event_type:
            return GLIMS_RESULT_TOPIC
        return GLIMS_RESULT_TOPIC

    def publish_event(self, event):
        if not self.enabled:
            LOGGER.info("Kafka disabled; skipping publish for event_id=%s", event.get("event_id"))
            return None
        if self._producer is None:
            raise KafkaPublishError("Kafka producer is not initialized")

        topic = self.route_event_to_topic(event)
        key = str(event.get("result_id") or event.get("event_id") or "")
        payload = json.dumps(event, ensure_ascii=True, default=_json_default).encode("utf-8")
        errors = []

        def delivery_report(error, message):
            if error is not None:
                errors.append(error)
                LOGGER.error("Kafka delivery failed for topic %s: %s", topic, error)

        try:
            self._producer.produce(topic=topic, key=key.encode("utf-8"), value=payload, callback=delivery_report)
            self._producer.flush(10)
        except Exception as exc:
            raise KafkaPublishError("Kafka publish failed for topic {}: {}".format(topic, exc)) from exc

        if errors:
            raise KafkaPublishError("Kafka delivery failed for topic {}: {}".format(topic, errors[0]))

        LOGGER.info("Published event_id=%s to topic=%s", event.get("event_id"), topic)
        return topic

    def publish_events(self, events):
        topics_used = []
        published_count = 0

        for event in events:
            topic = self.publish_event(event)
            if topic:
                published_count += 1
                topics_used.append(topic)

        unique_topics = sorted(set(topics_used))
        LOGGER.info("Published %d events to Kafka topics=%s", published_count, unique_topics)
        return {
            "published_count": published_count,
            "topics_used": unique_topics,
        }
