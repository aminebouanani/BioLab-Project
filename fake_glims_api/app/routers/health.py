"""Health endpoint."""

from fastapi import APIRouter, Request

from fake_glims_api.app.schemas.api_models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    event_store = request.app.state.event_store
    return HealthResponse(
        status="ok",
        service_name="fake-glims-api",
        loaded_events=event_store.count(),
        source_file=event_store.source_file,
    )
