"""Kafka consumer helper for local Redpanda testing."""

import json
import logging
from typing import Iterator

LOGGER = logging.getLogger(__name__)


class KafkaConsumerTool:
    def __init__(self, bootstrap_servers, topic, group_id="biolab-local-debug"):
        try:
            from confluent_kafka import Consumer
        except ImportError as exc:
            raise RuntimeError(
                "confluent-kafka is required. Install dependencies with "
                "'pip install -r requirements.txt'."
            ) from exc

        self.topic = topic
        self.consumer = Consumer(
            {
                "bootstrap.servers": bootstrap_servers,
                "group.id": group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
            }
        )
        self.consumer.subscribe([topic])

    def consume(self, max_messages=10, timeout_seconds=10) -> Iterator[dict]:
        empty_polls = 0
        consumed = 0
        while consumed < max_messages and empty_polls < timeout_seconds:
            message = self.consumer.poll(1.0)
            if message is None:
                empty_polls += 1
                continue
            if message.error():
                LOGGER.error("Kafka consumer error on topic %s: %s", self.topic, message.error())
                empty_polls += 1
                continue

            consumed += 1
            raw_value = message.value().decode("utf-8")
            try:
                yield json.loads(raw_value)
            except json.JSONDecodeError:
                yield {"raw_message": raw_value}

    def close(self):
        self.consumer.close()
