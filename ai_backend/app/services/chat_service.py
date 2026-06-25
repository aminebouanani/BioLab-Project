"""Report-scoped chat service."""

from ai_backend.app.ai_providers.base import AIProvider
from ai_backend.app.models.db_models import ChatMessage, ChatSession
from ai_backend.app.services.audit_service import AuditService
from ai_backend.app.services.gold_context_service import GoldContextService
from ai_backend.app.services.outdated_report_service import OutdatedReportService
from ai_backend.app.services.report_service import ReportNotFoundError, ReportService, ReportWorkflowError


class ChatService:
    def __init__(self, db, gold_context_service: GoldContextService, ai_provider: AIProvider):
        self.db = db
        self.gold_context_service = gold_context_service
        self.ai_provider = ai_provider
        self.report_service = ReportService(db, gold_context_service, ai_provider)
        self.audit = AuditService(db)

    def _session_for_report(self, report):
        session = self.db.query(ChatSession).filter(ChatSession.report_id == report.report_id).first()
        if session is None:
            session = ChatSession(report_id=report.report_id, patient_id=report.patient_id, order_id=report.order_id)
            self.db.add(session)
            self.db.flush()
        return session

    def ask(self, report_id: str, question: str):
        report = self.report_service.get_report(report_id)
        latest = self.report_service.latest_version(report_id)
        if latest is None:
            raise ReportNotFoundError("No report version exists for report: {}".format(report_id))
        outdated = OutdatedReportService(self.db, self.gold_context_service).check_report(report)
        if outdated["is_outdated"] or report.status == "OUTDATED":
            self.db.commit()
            raise ReportWorkflowError("Report is OUTDATED and must be regenerated before using chatbot.")

        context = self.gold_context_service.get_case(report.patient_id, report.order_id, report.specimen_id)
        answer = self.ai_provider.answer_question(latest.report_text, context, question)
        session = self._session_for_report(report)
        self.db.add(ChatMessage(chat_session_id=session.chat_session_id, report_id=report.report_id, role="user", message=question))
        self.db.add(ChatMessage(chat_session_id=session.chat_session_id, report_id=report.report_id, role="assistant", message=answer))
        self.audit.log("CHAT_QUESTION_ANSWERED", "report", report.report_id, report.patient_id, report.order_id, {"question": question})
        self.db.commit()
        return answer

    def history(self, report_id: str):
        report = self.report_service.get_report(report_id)
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.report_id == report.report_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
