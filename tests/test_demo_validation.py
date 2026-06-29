"""Tests for demo/pre-Azure validation utilities."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from scripts.demo import check_services
from scripts.demo.generate_demo_summary import load_summary
from scripts.demo.run_pre_azure_validation import ValidationError, _check_real_llm_health, _check_real_llm_response, run_validation
from scripts.demo.seed_demo_data import gold_context_has_data


class FakeResponse:
    def __init__(self, status_code=200, payload=None, content=b"", headers=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.content = content
        self.headers = headers or {"content-type": "application/json"}
        self.text = text or json.dumps(self._payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("HTTP {}".format(self.status_code))


class DemoValidationTests(unittest.TestCase):
    def test_validation_refuses_mock_provider_when_real_llm_required(self):
        with self.assertRaises(ValidationError):
            _check_real_llm_health(
                {
                    "configured_ai_provider": "mock_medgemma",
                    "active_provider": "mock_medgemma",
                    "require_real_llm": True,
                    "is_real_llm": False,
                    "model_name": "mock_medgemma",
                },
                True,
            )

    def test_validation_refuses_mock_report_response_when_real_llm_required(self):
        with self.assertRaises(ValidationError):
            _check_real_llm_response(
                {
                    "provider_used": "mock_medgemma",
                    "is_real_llm": False,
                    "model_name": "mock_medgemma",
                },
                True,
                "Report generation",
            )

    def test_health_checker_handles_unavailable_service(self):
        def fake_get(url, timeout=5):
            raise requests.ConnectionError("service unavailable")

        with patch("scripts.demo.check_services.requests.get", side_effect=fake_get):
            result = check_services.check_http_service("AI Backend", "http://127.0.0.1:8001/health")

        self.assertEqual(result.status, "FAIL")
        self.assertIn("service unavailable", result.details)

    def test_summary_generator_missing_file_is_clear(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / "missing.json"
            with self.assertRaises(FileNotFoundError):
                load_summary(missing_path)

    def test_seed_demo_data_detects_gold_context_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            gold_path = Path(temp_dir) / "data" / "gold" / "report_context"
            gold_path.mkdir(parents=True)
            self.assertFalse(gold_context_has_data(gold_path))
            (gold_path / "part-00000.parquet").write_bytes(b"placeholder")
            self.assertTrue(gold_context_has_data(gold_path))

    def test_run_pre_azure_validation_happy_path_with_mocked_backend(self):
        responses = []

        def fake_request(method, url, timeout=180, **kwargs):
            if url.endswith("/health"):
                return FakeResponse(
                    payload={
                        "configured_ai_provider": "remote_medgemma",
                        "active_provider": "remote_medgemma",
                        "require_real_llm": True,
                        "is_real_llm": True,
                        "model_name": "medgemma-4b-it",
                    }
                )
            if url.endswith("/cases"):
                return FakeResponse(
                    payload=[
                        {
                            "patient_id": "PAT-demo",
                            "order_id": "ORD-demo",
                            "specimen_id": "SPC-demo",
                            "status": "READY_FOR_AI",
                        }
                    ]
                )
            if url.endswith("/reports/generate"):
                return FakeResponse(
                    payload={
                        "report_id": "RPT-demo",
                        "report_text": "AI Draft Biological Report",
                        "model_name": "medgemma-4b-it",
                        "provider_used": "remote_medgemma",
                        "is_real_llm": True,
                    }
                )
            if url.endswith("/chat"):
                return FakeResponse(
                    payload={
                        "answer": "Remote MedGemma answer",
                        "model_name": "medgemma-4b-it",
                        "provider_used": "remote_medgemma",
                        "is_real_llm": True,
                    }
                )
            if url.endswith("/check-outdated"):
                return FakeResponse(payload={"is_outdated": False})
            if url.endswith("/validate"):
                return FakeResponse(payload={"status": "BIOLOGIST_VALIDATED"})
            if url.endswith("/generate-pdf"):
                return FakeResponse(
                    payload={
                        "export_id": "EXP-demo",
                        "pdf_filename": "report.pdf",
                        "export_status": "GENERATED",
                        "download_url": "/reports/RPT-demo/pdf/download",
                    }
                )
            if url.endswith("/pdf/download"):
                return FakeResponse(content=b"%PDF-demo", headers={"content-type": "application/pdf"})
            responses.append((method, url))
            return FakeResponse(status_code=404)

        with tempfile.TemporaryDirectory() as temp_dir:
            summary_path = Path(temp_dir) / "summary.json"
            with patch.dict(os.environ, {"REQUIRE_REAL_LLM": "true"}):
                with patch("scripts.demo.run_pre_azure_validation.requests.request", side_effect=fake_request):
                    summary = run_validation("http://backend.test", summary_path)

            self.assertEqual(summary["result"], "PASS")
            self.assertEqual(summary["provider_used"], "remote_medgemma")
            self.assertTrue(summary["is_real_llm"])
            self.assertTrue(summary_path.exists())


if __name__ == "__main__":
    unittest.main()
