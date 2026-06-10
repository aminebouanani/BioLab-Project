"""Reader for Synthea CSV laboratory observations."""

import csv
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, Optional, Set, Tuple

from .schemas import NormalizedLabResult

LOGGER = logging.getLogger(__name__)


def find_csv_pair(extraction_dir: Path) -> Optional[Tuple[Path, Path]]:
    """Find patients.csv and observations.csv from the same directory."""
    patient_files = sorted(extraction_dir.rglob("patients.csv"))
    for patients_path in patient_files:
        observations_path = patients_path.parent / "observations.csv"
        if observations_path.is_file():
            return patients_path, observations_path
    return None


def _parse_datetime(value: str) -> datetime:
    cleaned = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        for pattern in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(cleaned, pattern)
            except ValueError:
                continue
    raise ValueError("Unsupported result datetime: {}".format(value))


def _load_patient_ids(patients_path: Path) -> Set[str]:
    patient_ids = set()
    with patients_path.open("r", encoding="utf-8-sig", newline="") as input_file:
        for row in csv.DictReader(input_file):
            patient_id = (row.get("Id") or row.get("ID") or "").strip()
            if patient_id:
                patient_ids.add(patient_id)
    return patient_ids


def _looks_like_lab(row: Dict[str, str]) -> bool:
    category = (row.get("CATEGORY") or row.get("Category") or "").strip().lower()
    value = (row.get("VALUE") or row.get("Value") or "").strip()
    code = (row.get("CODE") or row.get("Code") or "").strip()
    return bool(value and code and ("laboratory" in category or category == "lab"))


def _observation_id(row: Dict[str, str], line_number: int) -> str:
    raw_id = (row.get("Id") or row.get("ID") or "").strip()
    if raw_id:
        return raw_id
    stable_fields = "|".join(
        [
            row.get("PATIENT", ""),
            row.get("ENCOUNTER", ""),
            row.get("CODE", ""),
            row.get("DATE", ""),
            str(line_number),
        ]
    )
    return hashlib.sha256(stable_fields.encode("utf-8")).hexdigest()


def read_csv_lab_results(
    patients_path: Path, observations_path: Path
) -> Iterator[NormalizedLabResult]:
    """Yield normalized lab results without exposing patient demographics."""
    patient_ids = _load_patient_ids(patients_path)
    LOGGER.info("Loaded %d patient IDs from %s", len(patient_ids), patients_path)

    with observations_path.open("r", encoding="utf-8-sig", newline="") as input_file:
        for line_number, row in enumerate(csv.DictReader(input_file), start=2):
            if not _looks_like_lab(row):
                continue

            patient_id = (row.get("PATIENT") or row.get("Patient") or "").strip()
            if not patient_id or patient_id not in patient_ids:
                LOGGER.warning("Skipping CSV observation at line %d with unknown patient", line_number)
                continue

            try:
                yield NormalizedLabResult(
                    source_patient_id=patient_id,
                    source_observation_id=_observation_id(row, line_number),
                    source_order_id=(row.get("ENCOUNTER") or "").strip() or None,
                    test_code=(row.get("CODE") or "").strip(),
                    loinc_code=(row.get("CODE") or "").strip() or None,
                    test_name=(row.get("DESCRIPTION") or "").strip(),
                    value=(row.get("VALUE") or "").strip(),
                    unit=(row.get("UNITS") or "").strip() or None,
                    validation_status="FINAL",
                    result_datetime=_parse_datetime(row.get("DATE") or ""),
                )
            except (ValueError, TypeError) as exc:
                LOGGER.warning("Skipping invalid CSV observation at line %d: %s", line_number, exc)
