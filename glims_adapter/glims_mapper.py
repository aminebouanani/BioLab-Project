"""Map normalized laboratory results to pseudonymized GLIMS-like events."""

import hashlib
import hmac
import uuid

from .schemas import GlimsLabResultEvent, NormalizedLabResult

EVENT_NAMESPACE = uuid.UUID("edfd8fc0-27fe-4dd0-9345-04878fc56d09")


def pseudonymize_patient_id(source_patient_id: str, secret: str) -> str:
    """Create a stable, non-reversible patient pseudonym."""
    if not secret:
        raise ValueError("GLIMS_HMAC_SECRET must not be empty")
    digest = hmac.new(
        secret.encode("utf-8"), source_patient_id.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return "PAT-{}".format(digest)


def _stable_id(prefix: str, value: str) -> str:
    return "{}-{}".format(prefix, uuid.uuid5(EVENT_NAMESPACE, value))


def map_to_glims_event(result: NormalizedLabResult, hmac_secret: str) -> GlimsLabResultEvent:
    """Map an internal normalized result into the public bronze event schema."""
    observation_key = "SYNTHEA|{}".format(result.source_observation_id)
    order_source = result.source_order_id or "{}|order".format(observation_key)
    specimen_source = result.source_specimen_id or "{}|specimen".format(order_source)

    return GlimsLabResultEvent(
        event_id=_stable_id("EVT", observation_key),
        patient_id=pseudonymize_patient_id(result.source_patient_id, hmac_secret),
        order_id=_stable_id("ORD", order_source),
        specimen_id=_stable_id("SPC", specimen_source),
        test_code=result.test_code,
        loinc_code=result.loinc_code,
        test_name=result.test_name,
        value=result.value,
        unit=result.unit,
        reference_range=result.reference_range,
        abnormal_flag=result.abnormal_flag,
        validation_status=result.validation_status,
        result_datetime=result.result_datetime,
    )
