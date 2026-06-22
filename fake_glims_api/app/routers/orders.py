"""Order-focused fake GLIMS endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, Request

from fake_glims_api.app.schemas.api_models import LabResultEvent
from fake_glims_api.app.services.event_store import NotFoundError

router = APIRouter()


@router.get("/orders/{order_id}/results", response_model=List[LabResultEvent])
def get_order_results(order_id: str, request: Request) -> List[LabResultEvent]:
    try:
        return request.app.state.query_service.get_order_results(order_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
