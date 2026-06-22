"""Result query endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from fake_glims_api.app.schemas.api_models import LabResultEvent
from fake_glims_api.app.services.event_store import NotFoundError

router = APIRouter()


@router.get("/results", response_model=List[LabResultEvent])
def get_results(
    request: Request,
    modified_after: Optional[datetime] = None,
    patient_id: Optional[str] = None,
    order_id: Optional[str] = None,
    limit: Optional[int] = Query(default=None, ge=1, le=10000),
) -> List[LabResultEvent]:
    try:
        return request.app.state.query_service.get_filtered_results(
            modified_after=modified_after,
            patient_id=patient_id,
            order_id=order_id,
            limit=limit,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
