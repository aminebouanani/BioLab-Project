"""Pydantic models exposed by the fake GLIMS API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LabResultEvent(ApiModel):
    event_id: str = Field(json_schema_extra={"example": "EVT-c95be046-c7ae-5933-9ff4-45531b3d74a6"})
    source_system: str = Field(json_schema_extra={"example": "GLIMS_SIM"})
    origin_source: str = Field(json_schema_extra={"example": "SYNTHEA"})
    event_type: str = Field(json_schema_extra={"example": "LAB_RESULT_CREATED"})
    patient_id: str = Field(json_schema_extra={"example": "PAT-a9ee29ccac507d42"})
    order_id: str = Field(json_schema_extra={"example": "ORD-a5b225b5-1661-5731-acbd-2260a4ec6953"})
    specimen_id: str = Field(json_schema_extra={"example": "SPC-0a83bda4-8c41-5ef5-89ad-d5f028a0bdcd"})
    test_code: str = Field(json_schema_extra={"example": "6690-2"})
    loinc_code: Optional[str] = None
    test_name: str = Field(json_schema_extra={"example": "Leukocytes [#/volume] in Blood by Automated count"})
    value: str = Field(json_schema_extra={"example": "3.9"})
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    abnormal_flag: Optional[str] = None
    validation_status: str = Field(json_schema_extra={"example": "FINAL"})
    result_datetime: datetime
    result_id: str = Field(json_schema_extra={"example": "RES-0c2770aa0cbb"})
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
    patient_id: str = Field(min_length=1, json_schema_extra={"example": "PAT-demo"})
    order_id: str = Field(min_length=1, json_schema_extra={"example": "ORD-demo"})
    specimen_id: str = Field(min_length=1, json_schema_extra={"example": "SPC-demo"})
    test_code: str = Field(min_length=1, json_schema_extra={"example": "6690-2"})
    loinc_code: Optional[str] = None
    test_name: str = Field(
        min_length=1,
        json_schema_extra={"example": "Leukocytes [#/volume] in Blood by Automated count"},
    )
    value: str = Field(min_length=1, json_schema_extra={"example": "4.2"})
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    abnormal_flag: Optional[str] = None
    validation_status: str = "PRELIMINARY"
    result_datetime: Optional[datetime] = None


class UpdateResultRequest(ApiModel):
    result_id: str = Field(min_length=1, json_schema_extra={"example": "RES-0c2770aa0cbb"})
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    abnormal_flag: Optional[str] = None
    validation_status: Optional[str] = None
    result_datetime: Optional[datetime] = None


class ValidateResultRequest(ApiModel):
    result_id: str = Field(min_length=1, json_schema_extra={"example": "RES-0c2770aa0cbb"})


class StreamPatientResponse(ApiModel):
    kafka_publishing_enabled: bool = False
    patient_id: str
    events_count: int
    published_count: int = 0
    topics_used: List[str] = Field(default_factory=list)
    events: List[LabResultEvent]


class StreamAllResponse(ApiModel):
    kafka_publishing_enabled: bool = False
    events_count: int
    published_count: int = 0
    topics_used: List[str] = Field(default_factory=list)


class StreamModifiedResponse(ApiModel):
    kafka_publishing_enabled: bool = False
    modified_after: datetime
    events_count: int
    published_count: int = 0
    topics_used: List[str] = Field(default_factory=list)
