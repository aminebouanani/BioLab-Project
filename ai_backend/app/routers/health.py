"""Health endpoint."""

from fastapi import APIRouter, Request
from sqlalchemy import text

from ai_backend.app.schemas.api_models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request):
    database_status = "ok"
    try:
        with request.app.state.SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"
    return HealthResponse(
        service_name="biolab-ai-backend",
        database_status=database_status,
        gold_context_path=str(request.app.state.settings.gold_report_context_path),
        ai_provider=request.app.state.ai_provider.model_name,
    )
