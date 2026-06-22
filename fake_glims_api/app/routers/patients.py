"""Patient-focused fake GLIMS endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, Request

from fake_glims_api.app.schemas.api_models import (
    LabResultEvent,
    OrderSummary,
    PatientSummary,
)
from fake_glims_api.app.services.event_store import NotFoundError

router = APIRouter()


@router.get("/patients", response_model=List[PatientSummary])
def get_patients(request: Request) -> List[PatientSummary]:
    return request.app.state.query_service.get_patients()


@router.get("/patients/{patient_id}/orders", response_model=List[OrderSummary])
def get_patient_orders(patient_id: str, request: Request) -> List[OrderSummary]:
    try:
        return request.app.state.query_service.get_patient_orders(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/patients/{patient_id}/results", response_model=List[LabResultEvent])
def get_patient_results(patient_id: str, request: Request) -> List[LabResultEvent]:
    try:
        return request.app.state.query_service.get_patient_results(patient_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
