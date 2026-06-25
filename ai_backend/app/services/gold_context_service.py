"""Read Gold report contexts from the local medallion output."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class GoldContextError(Exception):
    """Raised when Gold context cannot be loaded."""


def _json_safe(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float) and value != value:
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "tolist"):
        return _json_safe(value.tolist())
    return value


class GoldContextService:
    def __init__(self, gold_context_path: Path):
        self.gold_context_path = Path(gold_context_path)

    def _load_records(self) -> List[Dict[str, Any]]:
        if not self.gold_context_path.exists():
            raise GoldContextError(
                "Gold report context path does not exist: {}. Run the PySpark pipeline first.".format(
                    self.gold_context_path
                )
            )
        parquet_files = list(self.gold_context_path.glob("*.parquet"))
        json_files = list(self.gold_context_path.glob("*.json")) + list(self.gold_context_path.glob("*.jsonl"))
        if parquet_files:
            try:
                import pandas as pd
            except ImportError as exc:
                raise GoldContextError("pandas is required to read Gold Parquet context.") from exc
            try:
                frame = pd.read_parquet(str(self.gold_context_path))
            except Exception as exc:
                raise GoldContextError(
                    "Could not read Gold Parquet context at {}. Install pyarrow and verify the pipeline output.".format(
                        self.gold_context_path
                    )
                ) from exc
            return [_json_safe(row) for row in frame.to_dict(orient="records")]
        if json_files:
            records = []
            for json_path in json_files:
                with json_path.open("r", encoding="utf-8") as input_file:
                    for line in input_file:
                        if line.strip():
                            records.append(_json_safe(json.loads(line)))
            return records
        raise GoldContextError(
            "Gold report context path is empty: {}. Run the PySpark pipeline first.".format(
                self.gold_context_path
            )
        )

    def list_cases(self) -> List[Dict[str, Any]]:
        records = self._load_records()
        return sorted(records, key=lambda item: (item.get("patient_id", ""), item.get("order_id", ""), item.get("specimen_id", "")))

    def get_case(self, patient_id: str, order_id: str, specimen_id: Optional[str] = None) -> Dict[str, Any]:
        matches = [
            item
            for item in self.list_cases()
            if item.get("patient_id") == patient_id
            and item.get("order_id") == order_id
            and (specimen_id is None or item.get("specimen_id") == specimen_id)
        ]
        if not matches:
            raise GoldContextError("Gold context case not found for patient_id={}, order_id={}, specimen_id={}".format(patient_id, order_id, specimen_id))
        if specimen_id is None and len(matches) > 1:
            raise GoldContextError("Multiple specimens found for patient/order. Provide specimen_id.")
        return matches[0]

    def get_context_hash(self, patient_id: str, order_id: str, specimen_id: Optional[str] = None) -> str:
        return str(self.get_case(patient_id, order_id, specimen_id).get("context_hash"))
