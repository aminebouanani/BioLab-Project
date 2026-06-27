"""Report generation and lifecycle service."""

from typing import Optional

from ai_backend.app.ai_providers.base import AIProvider, AIProviderError
from ai_backend.app.models.db_models import BiologistAction, Report, ReportVersion
from ai_backend.app.services.audit_service import AuditService
from ai_backend.app.services.gold_context_service import GoldContextService
from ai_backend.app.services.outdated_report_service import OutdatedReportService


class ReportNotFoundError(Exception):
    pass


class ReportWorkflowError(Exception):
    pass


class ReportService:
    def __init__(self, db, gold_context_service: GoldContextService, ai_provider: AIProvider):
        self.db = db
        self.gold_context_service = gold_context_service
        self.ai_provider = ai_provider
        self.audit = AuditService(db)

    def get_report(self, report_id: str) -> Report:
        report = self.db.get(Report, report_id)
        if report is None:
            raise ReportNotFoundError("Report not found: {}".format(report_id))
        return report

    def latest_version(self, report_id: str):
        return (
            self.db.query(ReportVersion)
            .filter(ReportVersion.report_id == report_id)
            .order_by(ReportVersion.version_number.desc())
            .first()
        )

    def list_reports(self):
        return self.db.query(Report).order_by(Report.created_at.desc()).all()

    def _find_existing_report(self, patient_id: str, order_id: str, specimen_id: str):
        return (
            self.db.query(Report)
            .filter(
                Report.patient_id == patient_id,
                Report.order_id == order_id,
                Report.specimen_id == specimen_id,
            )
            .first()
        )

    def _create_version(self, report: Report, context, status="AI_DRAFT"):
        version_number = report.current_version + 1
        try:
            provider_result = self.ai_provider.generate_report(context)
        except AIProviderError as exc:
            raise ReportWorkflowError(str(exc))
        version = ReportVersion(
            report_id=report.report_id,
            version_number=version_number,
            source_context_hash=context["context_hash"],
            report_text=provider_result.text,
            model_name=provider_result.storage_model_name,
            status=status,
        )
        report.current_version = version_number
        report.status = status
        self.db.add(report)
        self.db.add(version)
        self.db.flush()
        return version, provider_result

    def generate_report(self, patient_id: str, order_id: str, specimen_id: Optional[str] = None):
        context = self.gold_context_service.get_case(patient_id, order_id, specimen_id)
        report = self._find_existing_report(context["patient_id"], context["order_id"], context["specimen_id"])
        if report is None:
            report = Report(
                patient_id=context["patient_id"],
                order_id=context["order_id"],
                specimen_id=context["specimen_id"],
                status="AI_DRAFT",
            )
            self.db.add(report)
            self.db.flush()
        version, provider_result = self._create_version(report, context)
        self.audit.log("REPORT_GENERATED", "report", report.report_id, report.patient_id, report.order_id, {"version": version.version_number})
        self.db.commit()
        return report, version, provider_result

    def regenerate_report(self, report_id: str):
        report = self.get_report(report_id)
        context = self.gold_context_service.get_case(report.patient_id, report.order_id, report.specimen_id)
        version, provider_result = self._create_version(report, context)
        self.audit.log("REPORT_REGENERATED", "report", report.report_id, report.patient_id, report.order_id, {"version": version.version_number})
        self.db.commit()
        return report, version, provider_result

    def validate_report(self, report_id: str, comment: Optional[str] = None):
        report = self.get_report(report_id)
        outdated = OutdatedReportService(self.db, self.gold_context_service).check_report(report)
        if outdated["is_outdated"]:
            self.db.commit()
            raise ReportWorkflowError("Report is OUTDATED and must be regenerated before validation.")
        report.status = "BIOLOGIST_VALIDATED"
        self.db.add(BiologistAction(report_id=report.report_id, action="VALIDATED", comment=comment))
        self.audit.log("REPORT_VALIDATED", "report", report.report_id, report.patient_id, report.order_id, {"comment": comment})
        self.db.commit()
        return report

    def reject_report(self, report_id: str, comment: Optional[str] = None):
        report = self.get_report(report_id)
        report.status = "REJECTED"
        self.db.add(report)
        self.db.add(BiologistAction(report_id=report.report_id, action="REJECTED", comment=comment))
        self.audit.log("REPORT_REJECTED", "report", report.report_id, report.patient_id, report.order_id, {"comment": comment})
        self.db.commit()
        return report
