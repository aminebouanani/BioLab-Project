"""Tests for final and draft PDF report exports."""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

from ai_backend.app.main import create_app
from ai_backend.app.models.db_models import ReportExport


class TestSettings:
    def __init__(self, database_url, gold_path, generated_reports_path):
        self.database_url = database_url
        self.data_lake_root = gold_path.parent.parent
        self.gold_report_context_path = gold_path
        self.generated_reports_path = generated_reports_path
        self.ai_provider = "mock_medgemma"
        self.ai_provider_fallback_to_mock = True
        self.require_real_llm = False
        self.medgemma_api_url = "http://localhost:9000"
        self.medgemma_api_key = ""
        self.medgemma_timeout_seconds = 180


def request(app, method, path, params=None, body=None):
    messages = []
    sent = False
    body_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": urlencode(params or {}).encode("ascii"),
        "headers": [(b"host", b"testserver"), (b"content-type", b"application/json")],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body_bytes, "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.get_event_loop().run_until_complete(app(scope, receive, send))
    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    headers = dict(
        (key.decode("latin-1"), value.decode("latin-1"))
        for key, value in next(message["headers"] for message in messages if message["type"] == "http.response.start")
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    content_type = headers.get("content-type", "")
    if content_type.startswith("application/json") and response_body:
        payload = json.loads(response_body.decode("utf-8"))
    else:
        payload = response_body
    return status, payload, headers


class PdfExportTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.gold_path = self.root / "data" / "gold" / "report_context"
        self.gold_path.mkdir(parents=True)
        self.generated_reports_path = self.root / "app_state" / "generated_reports"
        self.case = {
            "patient_id": "PAT-pdf",
            "order_id": "ORD-pdf",
            "specimen_id": "SPC-pdf",
            "results_count": 2,
            "abnormal_results_count": 1,
            "normal_results_count": 1,
            "unknown_flag_results_count": 0,
            "first_result_datetime": "2026-01-01T00:00:00Z",
            "last_result_datetime": "2026-01-01T00:05:00Z",
            "validation_status_summary": "FINAL",
            "status": "READY_FOR_AI",
            "context_hash": "hash-pdf-1",
            "generated_at": "2026-01-01T01:00:00Z",
            "results": [
                {
                    "result_id": "RES-pdf-1",
                    "test_code": "6690-2",
                    "loinc_code": "6690-2",
                    "test_name": "Leukocytes",
                    "value_raw": "12.0",
                    "value_numeric": 12.0,
                    "value_text": None,
                    "unit": "10*3/uL",
                    "reference_range": "4.0-10.0",
                    "abnormal_flag": "H",
                    "validation_status": "FINAL",
                    "result_datetime": "2026-01-01T00:00:00Z",
                    "modified_at": "2026-01-01T00:00:00Z",
                }
            ],
        }
        self._write_case(self.case)
        db_url = "sqlite:///{}".format((self.root / "app_state" / "test.db").as_posix())
        self.app = create_app(TestSettings(db_url, self.gold_path, self.generated_reports_path))

    def tearDown(self):
        self.app.state.engine.dispose()
        self.temp_dir.cleanup()

    def _write_case(self, payload):
        with (self.gold_path / "context.jsonl").open("w", encoding="utf-8") as output:
            output.write(json.dumps(payload) + "\n")

    def _generate_report(self):
        status, payload, _ = request(
            self.app,
            "POST",
            "/reports/generate",
            body={"patient_id": "PAT-pdf", "order_id": "ORD-pdf", "specimen_id": "SPC-pdf"},
        )
        self.assertEqual(status, 200)
        return payload

    def _validate_report(self, report_id):
        status, payload, _ = request(
            self.app,
            "POST",
            "/reports/{}/validate".format(report_id),
            body={"comment": "Validated for PDF export."},
        )
        self.assertEqual(status, 200)
        return payload

    def test_cannot_generate_final_pdf_for_missing_report(self):
        status, payload, _ = request(self.app, "POST", "/reports/RPT-missing/generate-pdf")
        self.assertEqual(status, 404)

    def test_cannot_generate_final_pdf_for_ai_draft_report(self):
        report = self._generate_report()
        status, payload, _ = request(self.app, "POST", "/reports/{}/generate-pdf".format(report["report_id"]))
        self.assertEqual(status, 409)
        self.assertIn("validated", payload["detail"])

    def test_cannot_generate_final_pdf_for_rejected_report(self):
        report = self._generate_report()
        status, payload, _ = request(
            self.app,
            "POST",
            "/reports/{}/reject".format(report["report_id"]),
            body={"comment": "Rejected."},
        )
        self.assertEqual(status, 200)
        status, payload, _ = request(self.app, "POST", "/reports/{}/generate-pdf".format(report["report_id"]))
        self.assertEqual(status, 409)
        self.assertIn("Rejected", payload["detail"])

    def test_cannot_generate_final_pdf_for_outdated_report(self):
        report = self._generate_report()
        self._validate_report(report["report_id"])
        changed = dict(self.case)
        changed["context_hash"] = "hash-pdf-2"
        self._write_case(changed)
        status, payload, _ = request(self.app, "POST", "/reports/{}/generate-pdf".format(report["report_id"]))
        self.assertEqual(status, 409)
        self.assertIn("OUTDATED", payload["detail"])

    def test_can_generate_final_pdf_for_validated_report(self):
        report = self._generate_report()
        self._validate_report(report["report_id"])
        status, payload, _ = request(self.app, "POST", "/reports/{}/generate-pdf".format(report["report_id"]))

        self.assertEqual(status, 200)
        self.assertEqual(payload["export_type"], "FINAL_PDF")
        self.assertEqual(payload["export_status"], "GENERATED")
        self.assertTrue((self.generated_reports_path / payload["pdf_filename"]).is_file())
        self.assertGreater(payload["file_size_bytes"], 0)

        with self.app.state.SessionLocal() as db:
            export_count = db.query(ReportExport).count()
        self.assertEqual(export_count, 1)

    def test_download_endpoint_returns_pdf_response(self):
        report = self._generate_report()
        self._validate_report(report["report_id"])
        status, payload, _ = request(self.app, "POST", "/reports/{}/generate-pdf".format(report["report_id"]))
        self.assertEqual(status, 200)

        status, body, headers = request(self.app, "GET", "/reports/{}/pdf/download".format(report["report_id"]))
        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/pdf")
        self.assertTrue(body.startswith(b"%PDF"))

    def test_draft_pdf_endpoint_marks_export_as_draft(self):
        report = self._generate_report()
        status, payload, _ = request(self.app, "POST", "/reports/{}/generate-draft-pdf".format(report["report_id"]))

        self.assertEqual(status, 200)
        self.assertEqual(payload["export_type"], "DRAFT_PDF")
        self.assertEqual(payload["export_status"], "GENERATED")
        self.assertTrue((self.generated_reports_path / payload["pdf_filename"]).is_file())


if __name__ == "__main__":
    unittest.main()
