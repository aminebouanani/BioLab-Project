"""Kafka topic names used by the local Redpanda streaming layer."""

GLIMS_PATIENT_TOPIC = "glims.patient"
GLIMS_ORDER_TOPIC = "glims.order"
GLIMS_SPECIMEN_TOPIC = "glims.specimen"
GLIMS_RESULT_TOPIC = "glims.result"
GLIMS_VALIDATION_TOPIC = "glims.validation"

ALL_TOPICS = [
    GLIMS_PATIENT_TOPIC,
    GLIMS_ORDER_TOPIC,
    GLIMS_SPECIMEN_TOPIC,
    GLIMS_RESULT_TOPIC,
    GLIMS_VALIDATION_TOPIC,
]
