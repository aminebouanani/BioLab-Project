"""Pydantic schemas for the AI backend API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())


class HealthResponse(ApiModel):
    service_name: str
    database_status: str
    gold_context_path: str
    ai_provider: str
    configured_ai_provider: str
    active_provider: str
    medgemma_api_url: Optional[str] = None
    remote_provider_reachable: bool
    fallback_to_mock: bool
    require_real_llm: bool
    provider_ready: bool
    model_name: Optional[str] = None
    is_real_llm: bool
    provider_error: Optional[str] = None


class CaseContext(ApiModel):
    patient_id: str
    order_id: str
    specimen_id: str
    results_count: int
    abnormal_results_count: int
    normal_results_count: int
    unknown_flag_results_count: int
    first_result_datetime: Optional[Any] = None
    last_result_datetime: Optional[Any] = None
    validation_status_summary: Optional[str] = None
    status: str
    context_hash: str
    generated_at: Optional[Any] = None
    results: List[Dict[str, Any]] = Field(default_factory=list)


class GenerateReportRequest(ApiModel):
    patient_id: str = Field(json_schema_extra={"example": "PAT-a9ee29cc"})
    order_id: str = Field(json_schema_extra={"example": "ORD-a5b225b5"})
    specimen_id: Optional[str] = Field(default=None, json_schema_extra={"example": "SPC-0a83bda4"})


class CommentRequest(ApiModel):
    comment: Optional[str] = Field(default=None, json_schema_extra={"example": "Reviewed and accepted."})


class ChatRequest(ApiModel):
    question: str = Field(json_schema_extra={"example": "Which results are abnormal in this report?"})


class ReportVersionResponse(ApiModel):
    report_version_id: str
    report_id: str
    version_number: int
    source_context_hash: str
    report_text: str
    model_name: str
    status: str
    created_at: datetime


class ReportResponse(ApiModel):
    report_id: str
    patient_id: str
    order_id: str
    specimen_id: str
    current_version: int
    status: str
    created_at: datetime
    updated_at: datetime
    latest_version: Optional[ReportVersionResponse] = None


class GenerateReportResponse(ApiModel):
    report_id: str
    version_number: int
    status: str
    source_context_hash: str
    report_text: str
    model_name: str
    ai_provider: str
    provider_used: str
    is_real_llm: bool


class OutdatedCheckResponse(ApiModel):
    report_id: str
    stored_source_context_hash: str
    current_context_hash: str
    is_outdated: bool
    status: str


class ChatResponse(ApiModel):
    report_id: str
    answer: str
    ai_provider: str
    model_name: str
    provider_used: str
    is_real_llm: bool


class ChatMessageResponse(ApiModel):
    role: str
    message: str
    created_at: datetime


class PdfExportResponse(ApiModel):
    export_id: str
    report_id: str
    report_version_id: str
    pdf_filename: str
    export_status: str
    export_type: str
    source_context_hash: str
    generated_at: datetime
    generated_by: Optional[str] = None
    file_size_bytes: Optional[int] = None
    download_url: str
