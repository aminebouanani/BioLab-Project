"""Command-line entry point for the Synthea to GLIMS adapter."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Iterable

from .glims_mapper import map_to_glims_event
from .schemas import GlimsLabResultEvent, NormalizedLabResult
from .synthea_csv_reader import find_csv_pair, read_csv_lab_results
from .synthea_fhir_reader import find_fhir_json, read_fhir_lab_results
from .unzip_synthea import extract_synthea_zips

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _zip_dir() -> Path:
    configured = os.getenv("SYNTHEA_ZIP_DIR")
    if configured:
        configured_path = _resolve_path(configured)
        if list(configured_path.glob("*.zip")):
            return configured_path
        LOGGER.warning(
            "Configured SYNTHEA_ZIP_DIR has no ZIP files: %s. Trying known local layouts.",
            configured_path,
        )

    candidates = [
        PROJECT_ROOT / "data/raw/synthea_zips",
        PROJECT_ROOT / "data/raw/sythea_zips",
        PROJECT_ROOT.parent / "data/raw/synthea_zips",
        PROJECT_ROOT.parent / "data/raw/sythea_zips",
    ]
    discovered = next((path for path in candidates if list(path.glob("*.zip"))), None)
    if discovered:
        LOGGER.info("Discovered Synthea ZIP directory: %s", discovered)
        return discovered

    checked = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(
        "No Synthea ZIP files found. Checked configured and known paths: {}".format(checked)
    )


def _model_json(event: GlimsLabResultEvent) -> str:
    if hasattr(event, "model_dump"):
        data: Dict[str, object] = event.model_dump(mode="json")
    else:
        data = json.loads(event.json())
    return json.dumps(data, ensure_ascii=True, separators=(",", ":"))


def _write_events(
    results: Iterable[NormalizedLabResult], output_path: Path, hmac_secret: str
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
        for result in results:
            output_file.write(_model_json(map_to_glims_event(result, hmac_secret)) + "\n")
            count += 1
    return count


def run() -> int:
    """Run extraction, source detection, mapping, and bronze JSONL writing."""
    _load_dotenv(PROJECT_ROOT / ".env")
    hmac_secret = os.getenv("GLIMS_HMAC_SECRET", "")
    if len(hmac_secret) < 32:
        raise ValueError("GLIMS_HMAC_SECRET must contain at least 32 characters")

    extraction_dir = _resolve_path(
        os.getenv("SYNTHEA_EXTRACTION_DIR", "data/extracted/synthea")
    )
    output_path = _resolve_path(
        os.getenv("GLIMS_OUTPUT_PATH", "data/bronze/glims_lab_results.jsonl")
    )
    extract_synthea_zips(_zip_dir(), extraction_dir)

    csv_pair = find_csv_pair(extraction_dir)
    if csv_pair:
        LOGGER.info("Using preferred CSV source: %s", csv_pair[1])
        results = read_csv_lab_results(*csv_pair)
    else:
        json_paths = find_fhir_json(extraction_dir)
        if not json_paths:
            raise FileNotFoundError("No Synthea CSV pair or FHIR JSON files found")
        LOGGER.info("CSV pair unavailable; using %d FHIR JSON files", len(json_paths))
        results = read_fhir_lab_results(json_paths)

    count = _write_events(results, output_path, hmac_secret)
    LOGGER.info("Wrote %d GLIMS_SIM LAB_RESULT_CREATED events to %s", count, output_path)
    return count


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    try:
        run()
    except Exception:
        LOGGER.exception("Adapter failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
