"""FastAPI entry point for the BioLab AI backend."""

from fastapi import FastAPI

from ai_backend.app.ai_providers.mock_medgemma import MockMedGemmaProvider
from ai_backend.app.config import Settings
from ai_backend.app.database import create_session_factory
from ai_backend.app.routers import cases, chat, health, reports
from ai_backend.app.services.gold_context_service import GoldContextService


def create_app(settings=None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(
        title="BioLab AI Backend",
        description="Report-first AI backend using local Gold context and a mock MedGemma provider.",
        version="0.1.0",
    )

    SessionLocal, engine = create_session_factory(settings.database_url)
    app.state.settings = settings
    app.state.SessionLocal = SessionLocal
    app.state.engine = engine
    app.state.gold_context_service = GoldContextService(settings.gold_report_context_path)
    app.state.ai_provider = MockMedGemmaProvider()

    app.include_router(health.router)
    app.include_router(cases.router)
    app.include_router(reports.router)
    app.include_router(chat.router)

    @app.get("/")
    def root():
        return {
            "service_name": "biolab-ai-backend",
            "message": "BioLab AI Backend is running.",
            "docs_url": "/docs",
            "health_url": "/health",
            "cases_url": "/cases",
            "reports_url": "/reports",
        }

    return app


app = create_app()
