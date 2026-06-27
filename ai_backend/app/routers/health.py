"""Health endpoint."""

from fastapi import APIRouter, Request
from sqlalchemy import text

from ai_backend.app.ai_providers.remote_medgemma import RemoteMedGemmaProvider
from ai_backend.app.schemas.api_models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(request: Request):
    settings = request.app.state.settings
    active_provider = request.app.state.ai_provider
    database_status = "ok"
    try:
        with request.app.state.SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"
    provider_error = None
    remote_provider_reachable = False
    provider_ready = False
    model_name = getattr(active_provider, "model_name", None)
    is_real_llm = bool(getattr(active_provider, "is_real_llm", False))

    if settings.ai_provider == "remote_medgemma":
        try:
            remote_provider = active_provider
            if getattr(active_provider, "provider_name", None) != "remote_medgemma":
                remote_provider = RemoteMedGemmaProvider(
                    settings.medgemma_api_url,
                    settings.medgemma_api_key,
                    settings.medgemma_timeout_seconds,
                    settings.require_real_llm,
                )
            remote_health = remote_provider.health()
            remote_provider_reachable = True
            provider_ready = bool(remote_health.get("ready"))
            model_name = remote_health.get("model_name") or model_name
            is_real_llm = bool(remote_health.get("is_real_llm"))
        except Exception as exc:
            provider_error = str(exc)
            provider_ready = False
    else:
        provider_ready = True
    fallback_to_mock = getattr(settings, "ai_provider_fallback_to_mock", True)
    require_real_llm = getattr(settings, "require_real_llm", False)
    medgemma_api_url = getattr(settings, "medgemma_api_url", "http://localhost:9000")

    return HealthResponse(
        service_name="biolab-ai-backend",
        database_status=database_status,
        gold_context_path=str(settings.gold_report_context_path),
        ai_provider=getattr(active_provider, "model_name", settings.ai_provider),
        configured_ai_provider=settings.ai_provider,
        active_provider=getattr(active_provider, "provider_name", "unknown"),
        medgemma_api_url=medgemma_api_url,
        remote_provider_reachable=remote_provider_reachable,
        fallback_to_mock=fallback_to_mock,
        require_real_llm=require_real_llm,
        provider_ready=provider_ready,
        model_name=model_name,
        is_real_llm=is_real_llm,
        provider_error=provider_error,
    )
