"""Focused tests for GLIMS event mapping and source detection."""

import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from pathlib import Path

from glims_adapter.glims_mapper import map_to_glims_event, pseudonymize_patient_id
from glims_adapter.main import _zip_dir
from glims_adapter.schemas import NormalizedLabResult
from glims_adapter.synthea_csv_reader import find_csv_pair


class GlimsMapperTests(unittest.TestCase):
    def setUp(self):
        self.result = NormalizedLabResult(
            source_patient_id="source-patient-123",
            source_observation_id="observation-456",
            source_order_id="encounter-789",
            test_code="2093-3",
            loinc_code="2093-3",
            test_name="Cholesterol",
            value="180",
            unit="mg/dL",
            result_datetime=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )

    def test_patient_pseudonym_is_deterministic_and_secret_dependent(self):
        first = pseudonymize_patient_id("patient-1", "a" * 32)
        second = pseudonymize_patient_id("patient-1", "a" * 32)
        different_secret = pseudonymize_patient_id("patient-1", "b" * 32)

        self.assertEqual(first, second)
        self.assertNotEqual(first, different_secret)
        self.assertNotIn("patient-1", first)

    def test_public_event_does_not_contain_source_identifiers(self):
        event = map_to_glims_event(self.result, "a" * 32)
        payload = event.model_dump() if hasattr(event, "model_dump") else event.dict()

        self.assertNotIn("source_patient_id", payload)
        self.assertNotIn("source_observation_id", payload)
        self.assertNotEqual(payload["patient_id"], self.result.source_patient_id)
        self.assertEqual(payload["source_system"], "GLIMS_SIM")
        self.assertEqual(payload["origin_source"], "SYNTHEA")
        self.assertEqual(payload["event_type"], "LAB_RESULT_CREATED")

    def test_mapping_is_stable_for_reprocessing(self):
        first = map_to_glims_event(self.result, "a" * 32)
        second = map_to_glims_event(self.result, "a" * 32)

        self.assertEqual(first.event_id, second.event_id)
        self.assertEqual(first.order_id, second.order_id)
        self.assertEqual(first.specimen_id, second.specimen_id)


class CsvDetectionTests(unittest.TestCase):
    def test_csv_pair_must_share_a_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_dir = root / "archive" / "csv"
            csv_dir.mkdir(parents=True)
            (csv_dir / "patients.csv").touch()
            (csv_dir / "observations.csv").touch()

            self.assertEqual(find_csv_pair(root), (csv_dir / "patients.csv", csv_dir / "observations.csv"))


class ZipDirectoryTests(unittest.TestCase):
    def test_missing_configured_path_falls_back_to_known_layout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "BioLab-Project"
            sibling_zip_dir = project_root.parent / "data" / "raw" / "sythea_zips"
            sibling_zip_dir.mkdir(parents=True)
            (sibling_zip_dir / "synthea.zip").touch()

            with patch("glims_adapter.main.PROJECT_ROOT", project_root), patch.dict(
                "os.environ", {"SYNTHEA_ZIP_DIR": "data/raw/synthea_zips"}
            ):
                self.assertEqual(_zip_dir(), sibling_zip_dir)


if __name__ == "__main__":
    unittest.main()
