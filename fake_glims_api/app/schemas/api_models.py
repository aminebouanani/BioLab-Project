"""Pydantic models exposed by the fake GLIMS API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LabResultEvent(ApiModel):
    event_id: str
    source_system: str
    origin_source: str
    event_type: str
    patient_id: str
    order_id: str
    specimen_id: str
    test_code: str
    loinc_code: Optional[str] = None
    test_name: str
    value: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    abnormal_flag: Optional[str] = None
    validation_status: str
    result_datetime: datetime
    result_id: str
    modified_at: datetime


class HealthResponse(ApiModel):
    status: str
    service_name: str
    loaded_events: int
    source_file: str


class PatientSummary(ApiModel):
    patient_id: str
    orders_count: int
    results_count: int


class OrderSummary(ApiModel):
    patient_id: str
    order_id: str
    specimen_id: str
    results_count: int
    first_result_datetime: datetime
    last_result_datetime: datetime


class NewResultRequest(ApiModel):
    patient_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    specimen_id: str = Field(min_length=1)
    test_code: str = Field(min_length=1)
    loinc_code: Optional[str] = None
    test_name: str = Field(min_length=1)
    value: str = Field(min_length=1)
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    abnormal_flag: Optional[str] = None
    validation_status: str = "PRELIMINARY"
    result_datetime: Optional[datetime] = None


class UpdateResultRequest(ApiModel):
    result_id: str = Field(min_length=1)
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    abnormal_flag: Optional[str] = None
    validation_status: Optional[str] = None
    result_datetime: Optional[datetime] = None


class ValidateResultRequest(ApiModel):
    result_id: str = Field(min_length=1)


class StreamPatientResponse(ApiModel):
    kafka_publishing_enabled: bool = False
    patient_id: str
    events_count: int
    events: List[LabResultEvent]
