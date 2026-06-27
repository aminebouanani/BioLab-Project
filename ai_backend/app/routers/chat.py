"""Report-first chatbot endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, Request

from ai_backend.app.schemas.api_models import ChatMessageResponse, ChatRequest, ChatResponse
from ai_backend.app.services.chat_service import ChatService
from ai_backend.app.services.gold_context_service import GoldContextError
from ai_backend.app.services.report_service import ReportNotFoundError, ReportWorkflowError

router = APIRouter(prefix="/reports")


@router.post("/{report_id}/chat", response_model=ChatResponse)
def ask_report_chat(report_id: str, payload: ChatRequest, request: Request):
    with request.app.state.SessionLocal() as db:
        service = ChatService(db, request.app.state.gold_context_service, request.app.state.ai_provider)
        try:
            provider_result = service.ask(report_id, payload.question)
            return ChatResponse(
                report_id=report_id,
                answer=provider_result.text,
                ai_provider=request.app.state.settings.ai_provider,
                model_name=provider_result.model_name,
                provider_used=provider_result.provider_used,
                is_real_llm=provider_result.is_real_llm,
            )
        except ReportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except GoldContextError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except ReportWorkflowError as exc:
            status_code = 502 if "Remote MedGemma" in str(exc) else 409
            raise HTTPException(status_code=status_code, detail=str(exc))


@router.get("/{report_id}/chat", response_model=List[ChatMessageResponse])
def get_report_chat(report_id: str, request: Request):
    with request.app.state.SessionLocal() as db:
        service = ChatService(db, request.app.state.gold_context_service, request.app.state.ai_provider)
        try:
            return [
                ChatMessageResponse(role=item.role, message=item.message, created_at=item.created_at)
                for item in service.history(report_id)
            ]
        except ReportNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
