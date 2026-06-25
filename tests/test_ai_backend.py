"""Tests for the report-first AI backend workflow."""

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

os.environ["AI_BACKEND_DATABASE_URL"] = "sqlite:///:memory:"

from ai_backend.app.config import Settings
from ai_backend.app.main import create_app


class TestSettings(Settings):
    def __init__(self, database_url, gold_path):
        self.database_url = database_url
        self.data_lake_root = gold_path.parent.parent
        self.gold_report_context_path = gold_path
        self.ai_provider = "mock_medgemma"


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
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return status, json.loads(response_body.decode("utf-8")) if response_body else None


class AIBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.gold_path = self.root / "data" / "gold" / "report_context"
        self.gold_path.mkdir(parents=True)
        self.case = {
            "patient_id": "PAT-test",
            "order_id": "ORD-test",
            "specimen_id": "SPC-test",
            "results_count": 2,
            "abnormal_results_count": 1,
            "normal_results_count": 1,
            "unknown_flag_results_count": 0,
            "first_result_datetime": "2026-01-01T00:00:00Z",
            "last_result_datetime": "2026-01-01T00:05:00Z",
            "validation_status_summary": "FINAL",
            "status": "READY_FOR_AI",
            "context_hash": "hash-1",
            "generated_at": "2026-01-01T01:00:00Z",
            "results": [
                {
                    "result_id": "RES-1",
                    "test_code": "6690-2",
                    "loinc_code": "6690-2",
                    "test_name": "Leukocytes",
                    "value_raw": "12.0",
                    "value_numeric": 12.0,
                    "value_text": None,
                    "unit": "10*3/uL",
                    "reference_range": None,
                    "abnormal_flag": "H",
                    "validation_status": "FINAL",
                    "result_datetime": "2026-01-01T00:00:00Z",
                    "modified_at": "2026-01-01T00:00:00Z",
                }
            ],
        }
        self._write_case(self.case)
        db_url = "sqlite:///{}".format((self.root / "app_state" / "test.db").as_posix())
        self.app = create_app(TestSettings(db_url, self.gold_path))

    def tearDown(self):
        self.app.state.engine.dispose()
        self.temp_dir.cleanup()

    def _write_case(self, payload):
        with (self.gold_path / "context.jsonl").open("w", encoding="utf-8") as output:
            output.write(json.dumps(payload) + "\n")

    def _generate_report(self):
        status, payload = request(
            self.app,
            "POST",
            "/reports/generate",
            body={"patient_id": "PAT-test", "order_id": "ORD-test", "specimen_id": "SPC-test"},
        )
        self.assertEqual(status, 200)
        return payload

    def test_health_endpoint(self):
        status, payload = request(self.app, "GET", "/health")

        self.assertEqual(status, 200)
        self.assertEqual(payload["service_name"], "biolab-ai-backend")
        self.assertEqual(payload["database_status"], "ok")

    def test_cases_endpoint(self):
        status, payload = request(self.app, "GET", "/cases")

        self.assertEqual(status, 200)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["patient_id"], "PAT-test")

    def test_report_generation_creates_report_and_version(self):
        payload = self._generate_report()

        self.assertEqual(payload["version_number"], 1)
        self.assertEqual(payload["status"], "AI_DRAFT")
        self.assertIn("AI Draft Biological Report", payload["report_text"])

    def test_chatbot_blocks_missing_report(self):
        status, payload = request(
            self.app,
            "POST",
            "/reports/RPT-missing/chat",
            body={"question": "Can I chat?"},
        )

        self.assertEqual(status, 404)

    def test_chatbot_works_after_report_generation(self):
        report = self._generate_report()

        status, payload = request(
            self.app,
            "POST",
            "/reports/{}/chat".format(report["report_id"]),
            body={"question": "What is abnormal?"},
        )

        self.assertEqual(status, 200)
        self.assertIn("Mock MedGemma answer", payload["answer"])

    def test_validate_blocks_outdated_report(self):
        report = self._generate_report()
        changed = dict(self.case)
        changed["context_hash"] = "hash-2"
        self._write_case(changed)

        status, payload = request(self.app, "POST", "/reports/{}/check-outdated".format(report["report_id"]))
        self.assertEqual(status, 200)
        self.assertTrue(payload["is_outdated"])

        status, payload = request(
            self.app,
            "POST",
            "/reports/{}/validate".format(report["report_id"]),
            body={"comment": "Looks fine"},
        )
        self.assertEqual(status, 409)

    def test_context_hash_comparison_is_deterministic(self):
        first = self._generate_report()
        status, payload = request(self.app, "POST", "/reports/{}/check-outdated".format(first["report_id"]))

        self.assertEqual(status, 200)
        self.assertFalse(payload["is_outdated"])
        self.assertEqual(payload["stored_source_context_hash"], payload["current_context_hash"])


if __name__ == "__main__":
    unittest.main()
