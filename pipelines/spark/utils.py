"""Shared helpers for the local medallion pipeline."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

NUMERIC_PATTERN = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)")


def parse_numeric_value(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = NUMERIC_PATTERN.search(str(value).strip())
    return float(match.group(0)) if match else None


def load_reference_ranges(path: Path) -> Dict[str, Dict[str, Any]]:
    if yaml is None:
        raise RuntimeError("pyyaml is required to load lab reference ranges")
    with path.open("r", encoding="utf-8") as input_file:
        payload = yaml.safe_load(input_file) or {}
    return payload.get("reference_ranges", {})


def abnormal_flag_for_value(loinc_code: str, value_numeric: Optional[float], ranges: Dict[str, Dict[str, Any]]) -> str:
    if value_numeric is None or not loinc_code:
        return "UNKNOWN"
    reference = ranges.get(str(loinc_code))
    if not reference:
        return "UNKNOWN"
    low = reference.get("low")
    high = reference.get("high")
    if low is not None and value_numeric < float(low):
        return "L"
    if high is not None and value_numeric > float(high):
        return "H"
    return "N"


def deterministic_context_hash(records: Iterable[Dict[str, Any]]) -> str:
    normalized = sorted(
        [
            {
                "patient_id": record.get("patient_id"),
                "order_id": record.get("order_id"),
                "specimen_id": record.get("specimen_id"),
                "result_id": record.get("result_id"),
                "test_code": record.get("test_code"),
                "value_raw": record.get("value_raw"),
                "unit": record.get("unit"),
                "abnormal_flag": record.get("abnormal_flag"),
                "validation_status": record.get("validation_status"),
                "modified_at": str(record.get("modified_at")),
            }
            for record in records
        ],
        key=lambda item: (
            item.get("patient_id") or "",
            item.get("order_id") or "",
            item.get("specimen_id") or "",
            item.get("result_id") or "",
        ),
    )
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_dataframe(df, output_path: Path, preferred_format: str = "parquet") -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.write.mode("overwrite").format(preferred_format).save(str(output_path))
        return preferred_format
    except Exception:
        fallback_path = Path(str(output_path) + "_json")
        df.write.mode("overwrite").json(str(fallback_path))
        return "json"


def read_medallion_dataframe(spark, path: Path):
    try:
        return spark.read.parquet(str(path))
    except Exception:
        return spark.read.json(str(path) + "_json")
