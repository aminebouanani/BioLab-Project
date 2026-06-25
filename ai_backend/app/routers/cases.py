"""Gold context case endpoints."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request

from ai_backend.app.schemas.api_models import CaseContext
from ai_backend.app.services.gold_context_service import GoldContextError

router = APIRouter()


@router.get("/cases", response_model=List[CaseContext])
def list_cases(request: Request):
    try:
        return request.app.state.gold_context_service.list_cases()
    except GoldContextError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/cases/{patient_id}/{order_id}", response_model=CaseContext)
def get_case(patient_id: str, order_id: str, request: Request, specimen_id: Optional[str] = None):
    try:
        return request.app.state.gold_context_service.get_case(patient_id, order_id, specimen_id)
    except GoldContextError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
