"""Tests for local Kafka/Redpanda streaming helpers."""

import unittest

from streaming.producer import KafkaProducerService
from streaming.topics import (
    GLIMS_ORDER_TOPIC,
    GLIMS_PATIENT_TOPIC,
    GLIMS_RESULT_TOPIC,
    GLIMS_SPECIMEN_TOPIC,
    GLIMS_VALIDATION_TOPIC,
)


class DisabledKafkaSettings:
    enabled = False
    bootstrap_servers = "localhost:9092"


class KafkaProducerRoutingTests(unittest.TestCase):
    def setUp(self):
        self.producer = KafkaProducerService(DisabledKafkaSettings())

    def test_topic_routing(self):
        cases = [
            ({"event_type": "LAB_RESULT_CREATED", "validation_status": "FINAL"}, GLIMS_RESULT_TOPIC),
            ({"event_type": "LAB_RESULT_UPDATED"}, GLIMS_RESULT_TOPIC),
            ({"event_type": "LAB_RESULT"}, GLIMS_RESULT_TOPIC),
            ({"event_type": "LAB_RESULT_VALIDATED"}, GLIMS_VALIDATION_TOPIC),
            ({"event_type": "VALIDATION_UPDATED"}, GLIMS_VALIDATION_TOPIC),
            ({"event_type": "PATIENT_UPDATED"}, GLIMS_PATIENT_TOPIC),
            ({"event_type": "PATIENT_CREATED"}, GLIMS_PATIENT_TOPIC),
            ({"event_type": "ORDER_CREATED"}, GLIMS_ORDER_TOPIC),
            ({"event_type": "ORDER_UPDATED"}, GLIMS_ORDER_TOPIC),
            ({"event_type": "SPECIMEN_CREATED"}, GLIMS_SPECIMEN_TOPIC),
            ({"event_type": "SPECIMEN_UPDATED"}, GLIMS_SPECIMEN_TOPIC),
            ({"event_type": "UNKNOWN"}, GLIMS_RESULT_TOPIC),
        ]

        for event, expected_topic in cases:
            self.assertEqual(self.producer.route_event_to_topic(event), expected_topic)

    def test_disabled_publish_does_not_crash(self):
        topic = self.producer.publish_event({"event_id": "EVT-test", "event_type": "LAB_RESULT_CREATED"})

        self.assertIsNone(topic)


if __name__ == "__main__":
    unittest.main()
