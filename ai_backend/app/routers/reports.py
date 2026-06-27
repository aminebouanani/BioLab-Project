"""Report lifecycle endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, Request

from ai_backend.app.routers.common import report_to_response
from ai_backend.app.schemas.api_models import (
    CommentRequest,
    GenerateReportRequest,
    GenerateReportResponse,
    OutdatedCheckResponse,
    ReportResponse,
)
from ai_backend.app.services.gold_context_service import GoldContextError
from ai_backend.app.services.outdated_report_service import OutdatedReportService
from ai_backend.app.services.report_service import ReportNotFoundError, ReportService, ReportWorkflowError

router = APIRouter(prefix="/reports")


def _report_service(request: Request, db):
    return ReportService(db, request.app.state.gold_context_service, request.app.state.ai_provider)


@router.post("/generate", response_model=GenerateReportResponse)
def generate_report(payload: GenerateReportRequest, request: Request):
    with request.app.state.SessionLocal() as db:
        try:
            report, version, provider_result = _report_service(request, db).generate_report(
                payload.patient_id, payload.order_id, payload.specimen_id
            )
            return GenerateReportResponse(
                report_id=report.report_id,
                version_number=version.version_number,
                status=report.status,
                source_context_hash=version.source_context_hash,
                report_text=version.report_text,
                model_name=provider_result.model_name,
                ai_provider=request.app.state.settings.ai_provider,
                provider_used=provider_result.provider_used,
                is_real_llm=provider_result.is_real_llm,
            )
        except GoldContextError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except ReportWorkflowError as exc:
            raise HTTPException(status_code=502, detail=str(exc))


@router.post("/{report_id}/regenerate", response_model=GenerateReportResponse)
def regenerate_report(report_id: str, request: Request):
    with request.app.state.SessionLocal() as db:
        try:
            report, version, provider_result = _report_service(request, db).regenerate_report(report_id)
            return GenerateReportResponse(
                report_id=report.report_id,
                version_number=version.version_number,
                status=report.status,
                source_context_hash=version.source_context_hash,
                report_text=version.report_text,
                model_name=provider_result.model_name,
                ai_provider=request.app.state.settings.ai_provider,
                provider_used=provider_result.provider_used,
                is_real_llm=provider_result.is_real_llm,
            )
        except ReportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except GoldContextError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except ReportWorkflowError as exc:
            raise HTTPException(status_code=502, detail=str(exc))


@router.post("/{report_id}/validate", response_model=ReportResponse)
def validate_report(report_id: str, payload: CommentRequest, request: Request):
    with request.app.state.SessionLocal() as db:
        service = _report_service(request, db)
        try:
            report = service.validate_report(report_id, payload.comment)
            return report_to_response(report, service.latest_version(report.report_id))
        except ReportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except (ReportWorkflowError, GoldContextError) as exc:
            raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{report_id}/reject", response_model=ReportResponse)
def reject_report(report_id: str, payload: CommentRequest, request: Request):
    with request.app.state.SessionLocal() as db:
        service = _report_service(request, db)
        try:
            report = service.reject_report(report_id, payload.comment)
            return report_to_response(report, service.latest_version(report.report_id))
        except ReportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{report_id}/check-outdated", response_model=OutdatedCheckResponse)
def check_outdated(report_id: str, request: Request):
    with request.app.state.SessionLocal() as db:
        service = _report_service(request, db)
        try:
            report = service.get_report(report_id)
            result = OutdatedReportService(db, request.app.state.gold_context_service).check_report(report)
            db.commit()
            return result
        except ReportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except GoldContextError as exc:
            raise HTTPException(status_code=409, detail=str(exc))


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: str, request: Request):
    with request.app.state.SessionLocal() as db:
        service = _report_service(request, db)
        try:
            report = service.get_report(report_id)
            return report_to_response(report, service.latest_version(report.report_id))
        except ReportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


@router.get("", response_model=List[ReportResponse])
def list_reports(request: Request):
    with request.app.state.SessionLocal() as db:
        service = _report_service(request, db)
        return [report_to_response(report, service.latest_version(report.report_id)) for report in service.list_reports()]
