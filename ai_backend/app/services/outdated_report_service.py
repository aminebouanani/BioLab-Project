"""Outdated report detection."""

from ai_backend.app.models.db_models import Report, ReportVersion
from ai_backend.app.services.gold_context_service import GoldContextService


class OutdatedReportService:
    def __init__(self, db, gold_context_service: GoldContextService):
        self.db = db
        self.gold_context_service = gold_context_service

    def latest_version(self, report: Report):
        return (
            self.db.query(ReportVersion)
            .filter(ReportVersion.report_id == report.report_id)
            .order_by(ReportVersion.version_number.desc())
            .first()
        )

    def check_report(self, report: Report):
        latest = self.latest_version(report)
        if latest is None:
            return {
                "report_id": report.report_id,
                "stored_source_context_hash": "",
                "current_context_hash": "",
                "is_outdated": True,
                "status": report.status,
            }
        current_hash = self.gold_context_service.get_context_hash(
            report.patient_id, report.order_id, report.specimen_id
        )
        is_outdated = latest.source_context_hash != current_hash
        if is_outdated and report.status != "OUTDATED":
            report.status = "OUTDATED"
            self.db.add(report)
            self.db.flush()
        return {
            "report_id": report.report_id,
            "stored_source_context_hash": latest.source_context_hash,
            "current_context_hash": current_hash,
            "is_outdated": is_outdated,
            "status": report.status,
        }
