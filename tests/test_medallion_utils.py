"""Tests for local medallion pipeline helper logic."""

import unittest

from pipelines.spark.utils import (
    abnormal_flag_for_value,
    deterministic_context_hash,
    parse_numeric_value,
)
from pipelines.spark.config import parse_java_major_version
from pipelines.spark.config import prepend_path_once


class MedallionUtilsTests(unittest.TestCase):
    def test_value_numeric_parsing(self):
        self.assertEqual(parse_numeric_value("3.9"), 3.9)
        self.assertEqual(parse_numeric_value("> 140 mg/dL"), 140.0)
        self.assertIsNone(parse_numeric_value("yellow"))

    def test_abnormal_flag_logic(self):
        ranges = {"6690-2": {"low": 4, "high": 11}}

        self.assertEqual(abnormal_flag_for_value("6690-2", 3.9, ranges), "L")
        self.assertEqual(abnormal_flag_for_value("6690-2", 12.0, ranges), "H")
        self.assertEqual(abnormal_flag_for_value("6690-2", 7.0, ranges), "N")
        self.assertEqual(abnormal_flag_for_value("unknown", 7.0, ranges), "UNKNOWN")
        self.assertEqual(abnormal_flag_for_value("6690-2", None, ranges), "UNKNOWN")

    def test_context_hash_is_deterministic(self):
        first = [
            {
                "patient_id": "PAT-1",
                "order_id": "ORD-1",
                "specimen_id": "SPC-1",
                "result_id": "RES-2",
                "test_code": "B",
                "value_raw": "2",
                "unit": "mg/dL",
                "abnormal_flag": "N",
                "validation_status": "FINAL",
                "modified_at": "2026-01-02T00:00:00Z",
            },
            {
                "patient_id": "PAT-1",
                "order_id": "ORD-1",
                "specimen_id": "SPC-1",
                "result_id": "RES-1",
                "test_code": "A",
                "value_raw": "1",
                "unit": "mg/dL",
                "abnormal_flag": "H",
                "validation_status": "FINAL",
                "modified_at": "2026-01-01T00:00:00Z",
            },
        ]
        second = list(reversed(first))

        self.assertEqual(deterministic_context_hash(first), deterministic_context_hash(second))

    def test_java_version_parser(self):
        self.assertEqual(parse_java_major_version('java version "1.8.0_402"'), 8)
        self.assertEqual(parse_java_major_version('openjdk version "17.0.11" 2024-04-16'), 17)
        self.assertEqual(parse_java_major_version('java version "23.0.1"'), 23)

    def test_prepend_path_once(self):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"PATH": "C:\\Existing"}, clear=False):
            prepend_path_once("C:\\Hadoop\\bin")
            prepend_path_once("C:\\Hadoop\\bin")
            self.assertEqual(os.environ["PATH"].split(os.pathsep).count("C:\\Hadoop\\bin"), 1)


if __name__ == "__main__":
    unittest.main()
