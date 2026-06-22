"""FastAPI entry point for the fake GLIMS integration simulator."""

import logging

from fastapi import FastAPI

from fake_glims_api.app.routers import health, orders, patients, results, simulate, stream
from fake_glims_api.app.services.event_store import EventStore
from fake_glims_api.app.services.query_service import QueryService
from fake_glims_api.app.services.simulation_service import SimulationService

LOGGER = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="BioLab Fake GLIMS API",
        description="Source/integration simulator for fake GLIMS lab-result events.",
        version="0.1.0",
    )

    event_store = EventStore()
    app.state.event_store = event_store
    app.state.query_service = QueryService(event_store)
    app.state.simulation_service = SimulationService(event_store)

    app.include_router(health.router)
    app.include_router(patients.router)
    app.include_router(orders.router)
    app.include_router(results.router)
    app.include_router(simulate.router)
    app.include_router(stream.router)

    @app.get("/")
    def root():
        return {
            "service_name": "fake-glims-api",
            "message": "BioLab Fake GLIMS API is running.",
            "docs_url": "/docs",
            "health_url": "/health",
            "patients_url": "/patients",
            "results_url": "/results",
        }

    LOGGER.info("Fake GLIMS API initialized with %d events", event_store.count())
    return app


app = create_app()
