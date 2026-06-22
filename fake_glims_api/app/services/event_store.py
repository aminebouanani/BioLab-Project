"""In-memory event store backed by the local fake GLIMS JSONL file."""

import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from fake_glims_api.app.schemas.api_models import LabResultEvent

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PRIMARY_EVENTS_PATH = PROJECT_ROOT / "data" / "bronze" / "glims_lab_results.jsonl"
SAMPLE_EVENTS_PATH = PROJECT_ROOT / "samples" / "glims_lab_results_sample.jsonl"


class EventStoreError(Exception):
    """Base exception for event-store failures."""


class NotFoundError(EventStoreError):
    """Raised when an entity is not present in the in-memory history."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def comparable_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def derive_result_id(event: Dict[str, Any]) -> str:
    raw_value = "|".join(
        [
            str(event.get("patient_id", "")),
            str(event.get("order_id", "")),
            str(event.get("specimen_id", "")),
            str(event.get("test_code", "")),
            str(event.get("result_datetime", "")),
        ]
    )
    return "RES-{}".format(hashlib.sha256(raw_value.encode("utf-8")).hexdigest())


def _model_dump(event: LabResultEvent) -> Dict[str, Any]:
    if hasattr(event, "model_dump"):
        return event.model_dump()
    return event.dict()


class EventStore:
    """Load fake GLIMS events and keep simulation events in memory."""

    def __init__(
        self,
        primary_path: Path = PRIMARY_EVENTS_PATH,
        fallback_path: Path = SAMPLE_EVENTS_PATH,
    ) -> None:
        self.primary_path = primary_path
        self.fallback_path = fallback_path
        self.source_path = self._select_source_path()
        self._lock = threading.Lock()
        self._events = self._load_events(self.source_path)

    def _select_source_path(self) -> Path:
        if self.primary_path.is_file():
            return self.primary_path
        if self.fallback_path.is_file():
            LOGGER.warning(
                "Full event file not found at %s; using sample file %s",
                self.primary_path,
                self.fallback_path,
            )
            return self.fallback_path
        raise FileNotFoundError(
            "No fake GLIMS event file found. Expected {} or {}.".format(
                self.primary_path, self.fallback_path
            )
        )

    def _load_events(self, source_path: Path) -> List[LabResultEvent]:
        events = []
        with source_path.open("r", encoding="utf-8") as source_file:
            for line_number, line in enumerate(source_file, start=1):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        "Invalid JSON in {} at line {}: {}".format(
                            source_path, line_number, exc
                        )
                    ) from exc
                events.append(self._normalize_event(payload, line_number))
        LOGGER.info("Loaded %d fake GLIMS events from %s", len(events), source_path)
        return events

    def _normalize_event(self, payload: Dict[str, Any], line_number: int = 0) -> LabResultEvent:
        if not isinstance(payload, dict):
            raise ValueError("Expected JSON object at line {}".format(line_number))
        normalized = dict(payload)
        normalized.setdefault("result_id", derive_result_id(normalized))
        normalized.setdefault("modified_at", normalized.get("result_datetime"))
        return LabResultEvent(**normalized)

    @property
    def source_file(self) -> str:
        return str(self.source_path)

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    def add_event(self, event: LabResultEvent) -> LabResultEvent:
        with self._lock:
            self._events.append(event)
        return event

    def all_events(self) -> List[LabResultEvent]:
        with self._lock:
            return list(self._events)

    def filter_events(
        self,
        patient_id: Optional[str] = None,
        order_id: Optional[str] = None,
        modified_after: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[LabResultEvent]:
        events = self.all_events()
        if patient_id:
            events = [event for event in events if event.patient_id == patient_id]
        if order_id:
            events = [event for event in events if event.order_id == order_id]
        if modified_after:
            threshold = comparable_datetime(modified_after)
            events = [
                event
                for event in events
                if comparable_datetime(event.modified_at) > threshold
            ]
        events.sort(key=lambda event: comparable_datetime(event.modified_at))
        return events[:limit] if limit is not None else events

    def latest_by_result_id(self, result_id: str) -> LabResultEvent:
        with self._lock:
            for event in reversed(self._events):
                if event.result_id == result_id:
                    return event
        raise NotFoundError("Result not found: {}".format(result_id))

    def has_patient(self, patient_id: str) -> bool:
        return any(event.patient_id == patient_id for event in self.all_events())

    def has_order(self, order_id: str) -> bool:
        return any(event.order_id == order_id for event in self.all_events())

    def events_for_patient(self, patient_id: str) -> List[LabResultEvent]:
        events = self.filter_events(patient_id=patient_id)
        if not events:
            raise NotFoundError("Patient not found: {}".format(patient_id))
        return events

    def events_for_order(self, order_id: str) -> List[LabResultEvent]:
        events = self.filter_events(order_id=order_id)
        if not events:
            raise NotFoundError("Order not found: {}".format(order_id))
        return events

    def result_history(self, result_id: str) -> Iterable[LabResultEvent]:
        return [event for event in self.all_events() if event.result_id == result_id]
