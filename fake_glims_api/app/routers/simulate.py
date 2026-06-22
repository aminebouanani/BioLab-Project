"""In-memory GLIMS event simulation endpoints."""

from fastapi import APIRouter, HTTPException, Request

from fake_glims_api.app.schemas.api_models import (
    LabResultEvent,
    NewResultRequest,
    UpdateResultRequest,
    ValidateResultRequest,
)
from fake_glims_api.app.services.event_store import NotFoundError

router = APIRouter(prefix="/simulate")


@router.post("/new-result", response_model=LabResultEvent)
def create_new_result(payload: NewResultRequest, request: Request) -> LabResultEvent:
    return request.app.state.simulation_service.create_new_result(payload)


@router.post("/update-result", response_model=LabResultEvent)
def update_result(payload: UpdateResultRequest, request: Request) -> LabResultEvent:
    try:
        return request.app.state.simulation_service.update_result(payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/validate-result", response_model=LabResultEvent)
def validate_result(payload: ValidateResultRequest, request: Request) -> LabResultEvent:
    try:
        return request.app.state.simulation_service.validate_result(payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
