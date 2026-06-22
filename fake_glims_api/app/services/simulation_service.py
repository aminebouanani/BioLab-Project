"""In-memory simulation of GLIMS result creation and changes."""

import uuid
from typing import Dict

from fake_glims_api.app.schemas.api_models import (
    LabResultEvent,
    NewResultRequest,
    UpdateResultRequest,
    ValidateResultRequest,
)
from fake_glims_api.app.services.event_store import (
    EventStore,
    _model_dump,
    derive_result_id,
    utc_now,
)


class SimulationService:
    def __init__(self, event_store: EventStore) -> None:
        self.event_store = event_store

    def _event_id(self, event_type: str) -> str:
        return "{}-{}".format(event_type.replace("LAB_RESULT_", "EVT-"), uuid.uuid4())

    def create_new_result(self, request: NewResultRequest) -> LabResultEvent:
        result_datetime = request.result_datetime or utc_now()
        payload: Dict[str, object] = {
            "event_id": self._event_id("LAB_RESULT_CREATED"),
            "source_system": "GLIMS_SIM",
            "origin_source": "SYNTHEA",
            "event_type": "LAB_RESULT_CREATED",
            "patient_id": request.patient_id,
            "order_id": request.order_id,
            "specimen_id": request.specimen_id,
            "test_code": request.test_code,
            "loinc_code": request.loinc_code,
            "test_name": request.test_name,
            "value": request.value,
            "unit": request.unit,
            "reference_range": request.reference_range,
            "abnormal_flag": request.abnormal_flag,
            "validation_status": request.validation_status,
            "result_datetime": result_datetime,
            "modified_at": utc_now(),
        }
        payload["result_id"] = derive_result_id(payload)
        event = LabResultEvent(**payload)
        return self.event_store.add_event(event)

    def update_result(self, request: UpdateResultRequest) -> LabResultEvent:
        previous = self.event_store.latest_by_result_id(request.result_id)
        payload = _model_dump(previous)
        payload.update(
            {
                "event_id": self._event_id("LAB_RESULT_UPDATED"),
                "event_type": "LAB_RESULT_UPDATED",
                "modified_at": utc_now(),
            }
        )

        for field_name in (
            "value",
            "unit",
            "reference_range",
            "abnormal_flag",
            "validation_status",
            "result_datetime",
        ):
            value = getattr(request, field_name)
            if value is not None:
                payload[field_name] = value

        event = LabResultEvent(**payload)
        return self.event_store.add_event(event)

    def validate_result(self, request: ValidateResultRequest) -> LabResultEvent:
        previous = self.event_store.latest_by_result_id(request.result_id)
        payload = _model_dump(previous)
        payload.update(
            {
                "event_id": self._event_id("LAB_RESULT_VALIDATED"),
                "event_type": "LAB_RESULT_VALIDATED",
                "validation_status": "FINAL",
                "modified_at": utc_now(),
            }
        )
        event = LabResultEvent(**payload)
        return self.event_store.add_event(event)
