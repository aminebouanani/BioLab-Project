"""Pydantic schemas used by the adapter."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AdapterModel(BaseModel):
    """Base model with strict field handling."""

    model_config = ConfigDict(extra="forbid")


class NormalizedLabResult(AdapterModel):
    """Internal, source-neutral laboratory result.

    The source patient ID is allowed only in this internal model and must never
    be serialized to the bronze output.
    """

    source_patient_id: str = Field(min_length=1)
    source_observation_id: str = Field(min_length=1)
    source_order_id: Optional[str] = None
    source_specimen_id: Optional[str] = None
    test_code: str = Field(min_length=1)
    loinc_code: Optional[str] = None
    test_name: str = Field(min_length=1)
    value: str = Field(min_length=1)
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    abnormal_flag: Optional[str] = None
    validation_status: str = "FINAL"
    result_datetime: datetime


class GlimsLabResultEvent(AdapterModel):
    """Public GLIMS-like LAB_RESULT event written to the bronze layer."""

    event_id: str = Field(min_length=1)
    source_system: str = "SYNTHEA"
    event_type: str = "LAB_RESULT"
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
    validation_status: str = Field(min_length=1)
    result_datetime: datetime
