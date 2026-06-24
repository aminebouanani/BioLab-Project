"""Small PySpark tests for Silver and Gold transformations."""

import tempfile
import unittest
from pathlib import Path

try:
    from pyspark.sql import SparkSession

    from pipelines.spark.config import PROJECT_ROOT, has_winutils, java_major_version
    from pipelines.spark.gold_report_context import build_gold_report_context
    from pipelines.spark.silver_lab_results import build_silver_lab_results

    PYSPARK_AVAILABLE = True
except ImportError:
    PYSPARK_AVAILABLE = False

JAVA_MAJOR_VERSION = java_major_version() if PYSPARK_AVAILABLE else None
WINUTILS_AVAILABLE = has_winutils(PROJECT_ROOT / "hadoop")
SPARK_RUNTIME_AVAILABLE = (
    PYSPARK_AVAILABLE
    and JAVA_MAJOR_VERSION is not None
    and JAVA_MAJOR_VERSION <= 17
    and WINUTILS_AVAILABLE
)


@unittest.skipUnless(SPARK_RUNTIME_AVAILABLE, "pyspark requires Java 8, 11, or 17 and hadoop/bin/winutils.exe")
class MedallionSparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = (
            SparkSession.builder.master("local[1]")
            .appName("BioLabMedallionTests")
            .config("spark.sql.session.timeZone", "UTC")
            .getOrCreate()
        )

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def _config(self, temp_dir):
        class Config:
            reference_ranges_path = Path(temp_dir) / "ranges.yml"

        Config.reference_ranges_path.write_text(
            "reference_ranges:\n"
            "  \"6690-2\":\n"
            "    low: 4\n"
            "    high: 11\n",
            encoding="utf-8",
        )
        return Config()

    def test_silver_keeps_latest_result_id_record(self):
        rows = [
            {
                "event_id": "EVT-1",
                "event_type": "LAB_RESULT_CREATED",
                "patient_id": "PAT-1",
                "order_id": "ORD-1",
                "specimen_id": "SPC-1",
                "result_id": "RES-1",
                "test_code": "6690-2",
                "loinc_code": "6690-2",
                "test_name": "Leukocytes",
                "value": "3.9",
                "unit": "10*3/uL",
                "validation_status": "final",
                "result_datetime": "2026-01-01T00:00:00Z",
                "modified_at": "2026-01-01T00:00:00Z",
            },
            {
                "event_id": "EVT-2",
                "event_type": "LAB_RESULT_UPDATED",
                "patient_id": "PAT-1",
                "order_id": "ORD-1",
                "specimen_id": "SPC-1",
                "result_id": "RES-1",
                "test_code": "6690-2",
                "loinc_code": "6690-2",
                "test_name": "Leukocytes",
                "value": "5.0",
                "unit": "10*3/uL",
                "validation_status": "final",
                "result_datetime": "2026-01-01T00:00:00Z",
                "modified_at": "2026-01-02T00:00:00Z",
            },
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            silver = build_silver_lab_results(self.spark, self._config(temp_dir), self.spark.createDataFrame(rows))
            records = silver.collect()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["event_id"], "EVT-2")
        self.assertEqual(records[0]["value_numeric"], 5.0)
        self.assertEqual(records[0]["abnormal_flag"], "N")

    def test_gold_groups_by_patient_order_specimen(self):
        rows = [
            {
                "patient_id": "PAT-1",
                "order_id": "ORD-1",
                "specimen_id": "SPC-1",
                "result_id": "RES-1",
                "test_code": "6690-2",
                "loinc_code": "6690-2",
                "test_name": "Leukocytes",
                "value_raw": "5.0",
                "value_numeric": 5.0,
                "value_text": None,
                "unit": "10*3/uL",
                "reference_range": None,
                "abnormal_flag": "N",
                "validation_status": "FINAL",
                "result_datetime": "2026-01-01T00:00:00Z",
                "modified_at": "2026-01-02T00:00:00Z",
                "is_latest": True,
            },
            {
                "patient_id": "PAT-1",
                "order_id": "ORD-1",
                "specimen_id": "SPC-1",
                "result_id": "RES-2",
                "test_code": "777-3",
                "loinc_code": "777-3",
                "test_name": "Platelets",
                "value_raw": "450",
                "value_numeric": 450.0,
                "value_text": None,
                "unit": "10*3/uL",
                "reference_range": None,
                "abnormal_flag": "N",
                "validation_status": "FINAL",
                "result_datetime": "2026-01-01T00:10:00Z",
                "modified_at": "2026-01-02T00:10:00Z",
                "is_latest": True,
            },
        ]
        gold = build_gold_report_context(self.spark, None, self.spark.createDataFrame(rows))
        record = gold.collect()[0]

        self.assertEqual(record["patient_id"], "PAT-1")
        self.assertEqual(record["order_id"], "ORD-1")
        self.assertEqual(record["specimen_id"], "SPC-1")
        self.assertEqual(record["results_count"], 2)
        self.assertEqual(record["status"], "READY_FOR_AI")
        self.assertTrue(record["context_hash"])


if __name__ == "__main__":
    unittest.main()
