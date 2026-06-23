"""Kafka/Redpanda streaming endpoints."""

from datetime import datetime
import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from fake_glims_api.app.schemas.api_models import (
    LabResultEvent,
    StreamAllResponse,
    StreamModifiedResponse,
    StreamPatientResponse,
)
from fake_glims_api.app.services.event_store import NotFoundError
from streaming.producer import KafkaPublishError

router = APIRouter(prefix="/stream")


def _event_payload(event: LabResultEvent) -> dict:
    if hasattr(event, "model_dump"):
        return event.model_dump(mode="json")
    return json.loads(event.json())


def _publish_if_enabled(request: Request, events: List[LabResultEvent]):
    kafka_producer = request.app.state.kafka_producer
    if not kafka_producer.enabled:
        return {
            "kafka_publishing_enabled": False,
            "published_count": 0,
            "topics_used": [],
        }

    try:
        publish_result = kafka_producer.publish_events([_event_payload(event) for event in events])
    except KafkaPublishError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {
        "kafka_publishing_enabled": True,
        "published_count": publish_result["published_count"],
        "topics_used": publish_result["topics_used"],
    }


@router.post("/patient/{patient_id}", response_model=StreamPatientResponse)
def stream_patient(patient_id: str, request: Request) -> StreamPatientResponse:
    try:
        events = request.app.state.query_service.get_patient_results(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    publish_info = _publish_if_enabled(request, events)
    return StreamPatientResponse(
        kafka_publishing_enabled=publish_info["kafka_publishing_enabled"],
        patient_id=patient_id,
        events_count=len(events),
        published_count=publish_info["published_count"],
        topics_used=publish_info["topics_used"],
        events=events,
    )


@router.post("/all", response_model=StreamAllResponse)
def stream_all(
    request: Request,
    limit: Optional[int] = Query(default=None, ge=1, le=100000),
) -> StreamAllResponse:
    events = request.app.state.query_service.get_filtered_results(limit=limit)
    publish_info = _publish_if_enabled(request, events)
    return StreamAllResponse(
        kafka_publishing_enabled=publish_info["kafka_publishing_enabled"],
        events_count=len(events),
        published_count=publish_info["published_count"],
        topics_used=publish_info["topics_used"],
    )


@router.post("/modified", response_model=StreamModifiedResponse)
def stream_modified(
    request: Request,
    modified_after: datetime,
    limit: Optional[int] = Query(default=None, ge=1, le=100000),
) -> StreamModifiedResponse:
    events = request.app.state.query_service.get_filtered_results(
        modified_after=modified_after,
        limit=limit,
    )
    publish_info = _publish_if_enabled(request, events)
    return StreamModifiedResponse(
        kafka_publishing_enabled=publish_info["kafka_publishing_enabled"],
        modified_after=modified_after,
        events_count=len(events),
        published_count=publish_info["published_count"],
        topics_used=publish_info["topics_used"],
    )
