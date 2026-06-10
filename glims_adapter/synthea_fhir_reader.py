"""Reader for Synthea FHIR JSON laboratory observations."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from .schemas import NormalizedLabResult

LOGGER = logging.getLogger(__name__)


def find_fhir_json(extraction_dir: Path) -> List[Path]:
    """Return candidate FHIR JSON files."""
    return sorted(extraction_dir.rglob("*.json"))


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))


def _reference_id(reference: Optional[str]) -> Optional[str]:
    if not reference:
        return None
    return reference.rstrip("/").split("/")[-1]


def _is_lab_observation(resource: Dict[str, Any]) -> bool:
    if resource.get("resourceType") != "Observation":
        return False
    categories = resource.get("category") or []
    return any(
        coding.get("code") in ("laboratory", "lab")
        for category in categories
        for coding in category.get("coding", [])
    )


def _coding(resource: Dict[str, Any]) -> Tuple[str, Optional[str], str]:
    code_block = resource.get("code") or {}
    codings = code_block.get("coding") or []
    loinc = next(
        (item for item in codings if "loinc.org" in item.get("system", "")),
        codings[0] if codings else {},
    )
    code = str(loinc.get("code") or "").strip()
    name = str(loinc.get("display") or code_block.get("text") or code).strip()
    return code, code if "loinc.org" in loinc.get("system", "") else None, name


def _value(resource: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    quantity = resource.get("valueQuantity")
    if quantity:
        return str(quantity.get("value", "")), quantity.get("unit") or quantity.get("code")
    if resource.get("valueString") is not None:
        return str(resource["valueString"]), None
    concept = resource.get("valueCodeableConcept") or {}
    return str(concept.get("text") or ""), None


def _reference_range(resource: Dict[str, Any]) -> Optional[str]:
    ranges = resource.get("referenceRange") or []
    if not ranges:
        return None
    item = ranges[0]
    if item.get("text"):
        return str(item["text"])
    low = item.get("low") or {}
    high = item.get("high") or {}
    unit = low.get("unit") or high.get("unit") or ""
    parts = [str(part.get("value")) for part in (low, high) if part.get("value") is not None]
    return " - ".join(parts) + (" {}".format(unit) if parts and unit else "") if parts else None


def _iter_resources(document: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    if document.get("resourceType") == "Bundle":
        for entry in document.get("entry") or []:
            resource = entry.get("resource")
            if isinstance(resource, dict):
                yield resource
    else:
        yield document


def read_fhir_lab_results(json_paths: List[Path]) -> Iterator[NormalizedLabResult]:
    """Yield normalized laboratory observations from FHIR JSON files."""
    for json_path in json_paths:
        try:
            with json_path.open("r", encoding="utf-8") as input_file:
                document = json.load(input_file)
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("Skipping unreadable FHIR file %s: %s", json_path, exc)
            continue

        for resource in _iter_resources(document):
            if not _is_lab_observation(resource):
                continue
            code, loinc_code, name = _coding(resource)
            value, unit = _value(resource)
            result_date = resource.get("effectiveDateTime") or resource.get("issued")
            patient_id = _reference_id((resource.get("subject") or {}).get("reference"))
            observation_id = str(resource.get("id") or "").strip()
            if not all((patient_id, observation_id, code, name, value, result_date)):
                LOGGER.warning("Skipping incomplete FHIR Observation in %s", json_path)
                continue

            interpretations = resource.get("interpretation") or []
            abnormal_flag = next(
                (
                    coding.get("code")
                    for interpretation in interpretations
                    for coding in interpretation.get("coding", [])
                    if coding.get("code")
                ),
                None,
            )
            try:
                yield NormalizedLabResult(
                    source_patient_id=patient_id,
                    source_observation_id=observation_id,
                    source_order_id=_reference_id(
                        ((resource.get("basedOn") or [{}])[0]).get("reference")
                    ),
                    source_specimen_id=_reference_id((resource.get("specimen") or {}).get("reference")),
                    test_code=code,
                    loinc_code=loinc_code,
                    test_name=name,
                    value=value,
                    unit=unit,
                    reference_range=_reference_range(resource),
                    abnormal_flag=abnormal_flag,
                    validation_status=str(resource.get("status") or "final").upper(),
                    result_datetime=_parse_datetime(result_date),
                )
            except (ValueError, TypeError) as exc:
                LOGGER.warning("Skipping invalid FHIR Observation in %s: %s", json_path, exc)
