"""PDF export endpoints for validated biological reports."""

from typing import List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from ai_backend.app.schemas.api_models import PdfExportResponse
from ai_backend.app.services.gold_context_service import GoldContextError
from ai_backend.app.services.pdf_service import PdfExportError, PdfExportService, PdfNotFoundError
from ai_backend.app.services.report_service import ReportNotFoundError, ReportService

router = APIRouter()


def _report_service(request: Request, db):
    return ReportService(db, request.app.state.gold_context_service, request.app.state.ai_provider)


def _pdf_service(request: Request, db):
    return PdfExportService(
        db,
        request.app.state.gold_context_service,
        _report_service(request, db),
        request.app.state.settings.generated_reports_path,
    )


def _export_to_response(export):
    return PdfExportResponse(
        export_id=export.export_id,
        report_id=export.report_id,
        report_version_id=export.report_version_id,
        pdf_filename=export.pdf_filename,
        export_status=export.export_status,
        export_type=export.export_type,
        source_context_hash=export.source_context_hash,
        generated_at=export.generated_at,
        generated_by=export.generated_by,
        file_size_bytes=export.file_size_bytes,
        download_url="/reports/{}/pdf/download".format(export.report_id),
    )


@router.post("/reports/{report_id}/generate-pdf", response_model=PdfExportResponse)
def generate_final_pdf(report_id: str, request: Request):
    with request.app.state.SessionLocal() as db:
        try:
            export = _pdf_service(request, db).generate_pdf(report_id, export_type="FINAL_PDF")
            return _export_to_response(export)
        except ReportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except (PdfExportError, GoldContextError) as exc:
            raise HTTPException(status_code=409, detail=str(exc))


@router.post("/reports/{report_id}/generate-draft-pdf", response_model=PdfExportResponse)
def generate_draft_pdf(report_id: str, request: Request):
    with request.app.state.SessionLocal() as db:
        try:
            export = _pdf_service(request, db).generate_pdf(report_id, export_type="DRAFT_PDF")
            return _export_to_response(export)
        except ReportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except (PdfExportError, GoldContextError) as exc:
            raise HTTPException(status_code=409, detail=str(exc))


@router.get("/reports/{report_id}/pdf", response_model=PdfExportResponse)
def get_latest_pdf_export(report_id: str, request: Request):
    with request.app.state.SessionLocal() as db:
        try:
            export = _pdf_service(request, db).get_latest_export(report_id)
            return _export_to_response(export)
        except ReportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except PdfNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


@router.get("/reports/{report_id}/pdf/download")
def download_latest_pdf(report_id: str, request: Request):
    with request.app.state.SessionLocal() as db:
        try:
            export, pdf_path = _pdf_service(request, db).latest_export_path(report_id)
            return FileResponse(
                str(pdf_path),
                media_type="application/pdf",
                filename=export.pdf_filename,
            )
        except ReportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except PdfNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))


@router.get("/pdf-exports", response_model=List[PdfExportResponse])
def list_pdf_exports(request: Request):
    with request.app.state.SessionLocal() as db:
        exports = _pdf_service(request, db).list_exports()
        return [_export_to_response(export) for export in exports]
