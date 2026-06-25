"""Router helpers."""

from ai_backend.app.schemas.api_models import ReportResponse, ReportVersionResponse


def version_to_response(version):
    if version is None:
        return None
    return ReportVersionResponse(
        report_version_id=version.report_version_id,
        report_id=version.report_id,
        version_number=version.version_number,
        source_context_hash=version.source_context_hash,
        report_text=version.report_text,
        model_name=version.model_name,
        status=version.status,
        created_at=version.created_at,
    )


def report_to_response(report, latest_version=None):
    return ReportResponse(
        report_id=report.report_id,
        patient_id=report.patient_id,
        order_id=report.order_id,
        specimen_id=report.specimen_id,
        current_version=report.current_version,
        status=report.status,
        created_at=report.created_at,
        updated_at=report.updated_at,
        latest_version=version_to_response(latest_version),
    )
