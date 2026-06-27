"""PDF export service for validated biological reports."""

import re
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ai_backend.app.models.db_models import BiologistAction, ReportExport
from ai_backend.app.services.audit_service import AuditService
from ai_backend.app.services.gold_context_service import GoldContextError, GoldContextService
from ai_backend.app.services.outdated_report_service import OutdatedReportService
from ai_backend.app.services.report_service import ReportNotFoundError, ReportService, ReportWorkflowError


class PdfExportError(Exception):
    pass


class PdfNotFoundError(Exception):
    pass


def _safe_filename(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _text(value):
    if value is None:
        return ""
    return str(value)


def _para_text(value):
    return escape(_text(value)).replace("\n", "<br/>")


def _provider_from_model_name(model_name):
    if model_name.startswith("remote_medgemma:"):
        return "remote_medgemma"
    if model_name == "mock_medgemma":
        return "mock_medgemma"
    return "unknown"


class PdfExportService:
    """Local filesystem PDF exporter.

    This storage boundary is intentionally small so it can later be replaced by
    Azure Blob Storage or Azure Data Lake Storage Gen2 without changing report
    workflow rules.
    """

    def __init__(self, db, gold_context_service: GoldContextService, report_service: ReportService, output_dir: Path):
        self.db = db
        self.gold_context_service = gold_context_service
        self.report_service = report_service
        self.output_dir = Path(output_dir)
        self.audit = AuditService(db)

    def _latest_validation_action(self, report_id):
        return (
            self.db.query(BiologistAction)
            .filter(BiologistAction.report_id == report_id, BiologistAction.action == "VALIDATED")
            .order_by(BiologistAction.created_at.desc())
            .first()
        )

    def _latest_export(self, report_id):
        return (
            self.db.query(ReportExport)
            .filter(ReportExport.report_id == report_id, ReportExport.export_status == "GENERATED")
            .order_by(ReportExport.generated_at.desc())
            .first()
        )

    def list_exports(self):
        return self.db.query(ReportExport).order_by(ReportExport.generated_at.desc()).all()

    def get_latest_export(self, report_id):
        report = self.report_service.get_report(report_id)
        export = self._latest_export(report.report_id)
        if export is None:
            raise PdfNotFoundError("No PDF export exists for report: {}".format(report_id))
        return export

    def latest_export_path(self, report_id):
        export = self.get_latest_export(report_id)
        pdf_path = Path(export.pdf_path)
        if not pdf_path.is_file():
            raise PdfNotFoundError("PDF file is missing on disk for export: {}".format(export.export_id))
        return export, pdf_path

    def _ensure_can_export(self, report, version, export_type):
        outdated = OutdatedReportService(self.db, self.gold_context_service).check_report(report)
        if outdated["is_outdated"] or report.status == "OUTDATED":
            self.db.commit()
            raise PdfExportError("Report is OUTDATED and must be regenerated before PDF export.")
        if version is None:
            raise PdfExportError("Report has no version to export.")
        if export_type == "FINAL_PDF":
            if report.status == "AI_DRAFT":
                raise PdfExportError("Report must be validated before generating an official final PDF.")
            if report.status == "REJECTED":
                raise PdfExportError("Rejected reports cannot generate official final PDFs.")
            if report.status != "BIOLOGIST_VALIDATED":
                raise PdfExportError("Only BIOLOGIST_VALIDATED reports can generate official final PDFs.")
        if export_type == "DRAFT_PDF" and report.status in ("REJECTED", "OUTDATED"):
            raise PdfExportError("Rejected or outdated reports cannot generate draft PDFs.")

    def _styles(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="CenterTitle", parent=styles["Title"], alignment=TA_CENTER))
        styles.add(ParagraphStyle(name="DraftWarning", parent=styles["Heading1"], alignment=TA_CENTER, textColor=colors.red))
        styles.add(ParagraphStyle(name="SmallBody", parent=styles["BodyText"], fontSize=8, leading=10))
        return styles

    def _build_pdf(self, pdf_path, report, version, context, export_id, export_type, generated_at):
        styles = self._styles()
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=1.3 * cm,
            leftMargin=1.3 * cm,
            topMargin=1.2 * cm,
            bottomMargin=1.2 * cm,
        )
        story = []
        story.append(Paragraph("BioLab Medical AI", styles["CenterTitle"]))
        story.append(Paragraph("AI-assisted biological report", styles["Heading2"]))
        if export_type == "DRAFT_PDF":
            story.append(Paragraph("DRAFT - NOT VALIDATED - NOT FOR CLINICAL USE", styles["DraftWarning"]))
        story.append(Spacer(1, 0.3 * cm))

        validation_action = self._latest_validation_action(report.report_id)
        case_rows = [
            ["Generated PDF date/time", _text(generated_at)],
            ["Report ID", report.report_id],
            ["Report version", _text(report.current_version)],
            ["Patient ID", report.patient_id],
            ["Order ID", report.order_id],
            ["Specimen ID", report.specimen_id],
            ["Context hash", _text(context.get("context_hash"))],
            ["Source context hash", version.source_context_hash],
        ]
        story.append(Paragraph("Case identifiers", styles["Heading2"]))
        story.append(self._two_column_table(case_rows))

        context_rows = [
            ["Results count", _text(context.get("results_count"))],
            ["Abnormal results count", _text(context.get("abnormal_results_count"))],
            ["Normal results count", _text(context.get("normal_results_count"))],
            ["Unknown flag results count", _text(context.get("unknown_flag_results_count"))],
            ["Validation status summary", _text(context.get("validation_status_summary"))],
            ["First result datetime", _text(context.get("first_result_datetime"))],
            ["Last result datetime", _text(context.get("last_result_datetime"))],
        ]
        story.append(Paragraph("Laboratory context", styles["Heading2"]))
        story.append(self._two_column_table(context_rows))

        story.append(Paragraph("Results table", styles["Heading2"]))
        story.append(self._results_table(context.get("results") or [], styles))
        story.append(PageBreak())

        story.append(Paragraph("AI-assisted interpretation", styles["Heading2"]))
        for block in version.report_text.split("\n\n"):
            story.append(Paragraph(_para_text(block), styles["BodyText"]))
            story.append(Spacer(1, 0.15 * cm))

        story.append(Paragraph("Validation section", styles["Heading2"]))
        validation_rows = [
            ["Report status", report.status],
            ["Validation date", _text(getattr(validation_action, "created_at", ""))],
            ["Biologist comment", _text(getattr(validation_action, "comment", ""))],
        ]
        story.append(self._two_column_table(validation_rows))

        provider_used = _provider_from_model_name(version.model_name)
        trace_rows = [
            ["Model name", version.model_name],
            ["AI provider / provider used", provider_used],
            ["Report version ID", version.report_version_id],
            ["Source context hash", version.source_context_hash],
            ["PDF export ID", export_id],
            ["Generated at", _text(generated_at)],
        ]
        story.append(Paragraph("Traceability section", styles["Heading2"]))
        story.append(self._two_column_table(trace_rows))

        story.append(Paragraph("Disclaimer", styles["Heading2"]))
        story.append(
            Paragraph(
                "This document was generated from an AI-assisted draft and requires/reflects "
                "biologist validation. The AI output does not replace professional medical judgment.",
                styles["BodyText"],
            )
        )
        if export_type == "DRAFT_PDF":
            story.append(Paragraph("DRAFT - NOT VALIDATED - NOT FOR CLINICAL USE", styles["DraftWarning"]))

        doc.build(story)

    def _two_column_table(self, rows):
        table = Table(rows, colWidths=[5 * cm, 12 * cm], hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f3f7")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("LEADING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        return table

    def _results_table(self, results, styles):
        header = ["Test name", "LOINC", "Value", "Unit", "Reference", "Flag", "Status", "Datetime"]
        rows = [header]
        for item in results:
            rows.append(
                [
                    Paragraph(_para_text(item.get("test_name")), styles["SmallBody"]),
                    _text(item.get("loinc_code")),
                    _text(item.get("value_raw")),
                    _text(item.get("unit")),
                    _text(item.get("reference_range")),
                    _text(item.get("abnormal_flag")),
                    _text(item.get("validation_status")),
                    _text(item.get("result_datetime")),
                ]
            )
        table = Table(rows, repeatRows=1, colWidths=[4.3 * cm, 2 * cm, 1.6 * cm, 1.7 * cm, 2 * cm, 1.2 * cm, 1.7 * cm, 3 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("LEADING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table

    def generate_pdf(self, report_id, export_type="FINAL_PDF", generated_by="local-biologist"):
        report = self.report_service.get_report(report_id)
        version = self.report_service.latest_version(report.report_id)
        self._ensure_can_export(report, version, export_type)
        context = self.gold_context_service.get_case(report.patient_id, report.order_id, report.specimen_id)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        export = ReportExport(
            report_id=report.report_id,
            report_version_id=version.report_version_id,
            pdf_filename="pending.pdf",
            pdf_path="pending.pdf",
            export_status="GENERATED",
            source_context_hash=version.source_context_hash,
            generated_by=generated_by,
            export_type=export_type,
        )
        self.db.add(export)
        self.db.flush()

        filename = "{}_{}_v{}.pdf".format(
            _safe_filename(export_type.lower()),
            _safe_filename(report.report_id),
            version.version_number,
        )
        pdf_path = self.output_dir / filename
        try:
            self._build_pdf(pdf_path, report, version, context, export.export_id, export_type, export.generated_at)
            export.pdf_filename = filename
            export.pdf_path = str(pdf_path)
            export.file_size_bytes = pdf_path.stat().st_size
            self.db.add(export)
            self.audit.log(
                "DRAFT_PDF_GENERATED" if export_type == "DRAFT_PDF" else "PDF_GENERATED",
                "report_export",
                export.export_id,
                report.patient_id,
                report.order_id,
                {
                    "report_id": report.report_id,
                    "report_version_id": version.report_version_id,
                    "export_id": export.export_id,
                    "pdf_filename": filename,
                    "export_type": export_type,
                    "source_context_hash": version.source_context_hash,
                },
            )
            self.db.commit()
            return export
        except Exception as exc:
            export.export_status = "FAILED"
            self.db.add(export)
            self.audit.log(
                "PDF_GENERATION_FAILED",
                "report_export",
                export.export_id,
                report.patient_id,
                report.order_id,
                {
                    "report_id": report.report_id,
                    "report_version_id": version.report_version_id,
                    "export_id": export.export_id,
                    "pdf_filename": filename,
                    "export_type": export_type,
                    "source_context_hash": version.source_context_hash,
                    "error": str(exc),
                },
            )
            self.db.commit()
            raise PdfExportError("PDF generation failed: {}".format(exc))
