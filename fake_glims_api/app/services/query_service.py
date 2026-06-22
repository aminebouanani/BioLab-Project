"""Read-model queries for the fake GLIMS API."""

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from fake_glims_api.app.schemas.api_models import (
    LabResultEvent,
    OrderSummary,
    PatientSummary,
)
from fake_glims_api.app.services.event_store import EventStore, NotFoundError


class QueryService:
    def __init__(self, event_store: EventStore) -> None:
        self.event_store = event_store

    def get_patients(self) -> List[PatientSummary]:
        orders_by_patient: Dict[str, Set[str]] = defaultdict(set)
        results_by_patient: Dict[str, Set[str]] = defaultdict(set)

        for event in self.event_store.all_events():
            orders_by_patient[event.patient_id].add(event.order_id)
            results_by_patient[event.patient_id].add(event.result_id)

        return [
            PatientSummary(
                patient_id=patient_id,
                orders_count=len(orders_by_patient[patient_id]),
                results_count=len(results_by_patient[patient_id]),
            )
            for patient_id in sorted(orders_by_patient)
        ]

    def get_patient_orders(self, patient_id: str) -> List[OrderSummary]:
        events = self.event_store.events_for_patient(patient_id)
        grouped: Dict[Tuple[str, str], List[LabResultEvent]] = defaultdict(list)
        for event in events:
            grouped[(event.order_id, event.specimen_id)].append(event)

        summaries = []
        for (order_id, specimen_id), order_events in grouped.items():
            result_datetimes = [event.result_datetime for event in order_events]
            result_ids = set(event.result_id for event in order_events)
            summaries.append(
                OrderSummary(
                    patient_id=patient_id,
                    order_id=order_id,
                    specimen_id=specimen_id,
                    results_count=len(result_ids),
                    first_result_datetime=min(result_datetimes),
                    last_result_datetime=max(result_datetimes),
                )
            )
        summaries.sort(key=lambda item: item.first_result_datetime)
        return summaries

    def get_patient_results(self, patient_id: str) -> List[LabResultEvent]:
        return self.event_store.events_for_patient(patient_id)

    def get_order_results(self, order_id: str) -> List[LabResultEvent]:
        return self.event_store.events_for_order(order_id)

    def get_filtered_results(
        self,
        modified_after: Optional[datetime] = None,
        patient_id: Optional[str] = None,
        order_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[LabResultEvent]:
        if patient_id and not self.event_store.has_patient(patient_id):
            raise NotFoundError("Patient not found: {}".format(patient_id))
        if order_id and not self.event_store.has_order(order_id):
            raise NotFoundError("Order not found: {}".format(order_id))
        return self.event_store.filter_events(
            patient_id=patient_id,
            order_id=order_id,
            modified_after=modified_after,
            limit=limit,
        )
