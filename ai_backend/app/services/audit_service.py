"""Audit logging service."""

import json
from typing import Any, Dict, Optional

from ai_backend.app.models.db_models import AuditLog


class AuditService:
    def __init__(self, db):
        self.db = db

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        patient_id: Optional[str] = None,
        order_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.db.add(
            AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                patient_id=patient_id,
                order_id=order_id,
                details_json=json.dumps(details or {}, sort_keys=True),
            )
        )
