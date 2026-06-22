"""Kafka-placeholder streaming endpoints."""

from fastapi import APIRouter, HTTPException, Request

from fake_glims_api.app.schemas.api_models import StreamPatientResponse
from fake_glims_api.app.services.event_store import NotFoundError

router = APIRouter(prefix="/stream")


@router.post("/patient/{patient_id}", response_model=StreamPatientResponse)
def stream_patient(patient_id: str, request: Request) -> StreamPatientResponse:
    try:
        events = request.app.state.query_service.get_patient_results(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return StreamPatientResponse(
        kafka_publishing_enabled=False,
        patient_id=patient_id,
        events_count=len(events),
        events=events,
    )
