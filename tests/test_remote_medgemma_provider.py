"""Tests for remote MedGemma provider integration without loading a real model."""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

import requests

from ai_backend.app.ai_providers.base import AIProviderConfigurationError
from ai_backend.app.ai_providers.factory import create_ai_provider
from ai_backend.app.main import create_app


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class RemoteSettings:
    def __init__(self, database_url="sqlite:///:memory:", gold_path=None, fallback=False, require_real=True):
        self.database_url = database_url
        self.data_lake_root = Path(".")
        self.gold_report_context_path = gold_path or Path(".")
        self.ai_provider = "remote_medgemma"
        self.ai_provider_fallback_to_mock = fallback
        self.require_real_llm = require_real
        self.medgemma_api_url = "http://remote-medgemma.test"
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
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return status, json.loads(response_body.decode("utf-8")) if response_body else None


def fake_remote_request(self, method, url, headers=None, json=None, timeout=None):
    if url.endswith("/health"):
        return FakeResponse(
            200,
            {
                "service": "medgemma-server",
                "status": "ok",
                "model_loaded": True,
                "model_name": "medgemma-4b-it",
                "provider": "remote_medgemma",
                "is_real_llm": True,
            },
        )
    if url.endswith("/generate-report"):
        return FakeResponse(
            200,
            {
                "model_name": "medgemma-4b-it",
                "provider": "remote_medgemma",
                "is_real_llm": True,
                "report_text": "AI Draft Biological Report\nRemote real model draft.",
            },
        )
    if url.endswith("/answer-question"):
        return FakeResponse(
            200,
            {
                "model_name": "medgemma-4b-it",
                "provider": "remote_medgemma",
                "is_real_llm": True,
                "answer": "Remote real model answer.",
            },
        )
    return FakeResponse(404, {"detail": "not found"})


def unreachable_request(self, method, url, headers=None, json=None, timeout=None):
    raise requests.ConnectionError("no route to host")


class RemoteMedGemmaProviderTests(unittest.TestCase):
    def setUp(self):
        self.original_request = requests.Session.request

    def tearDown(self):
        requests.Session.request = self.original_request

    def test_factory_returns_remote_provider(self):
        requests.Session.request = fake_remote_request
        provider = create_ai_provider(RemoteSettings())
        self.assertEqual(provider.provider_name, "remote_medgemma")

    def test_unreachable_remote_falls_back_when_allowed(self):
        requests.Session.request = unreachable_request
        provider = create_ai_provider(RemoteSettings(fallback=True, require_real=False))
        self.assertEqual(provider.provider_name, "mock_medgemma")

    def test_strict_mode_blocks_mock_fallback(self):
        requests.Session.request = unreachable_request
        with self.assertRaises(AIProviderConfigurationError):
            create_ai_provider(RemoteSettings(fallback=True, require_real=True))

    def test_health_reports_remote_provider_status(self):
        requests.Session.request = fake_remote_request
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gold_path = root / "data" / "gold" / "report_context"
            gold_path.mkdir(parents=True)
            settings = RemoteSettings(
                database_url="sqlite:///{}".format((root / "app_state" / "test.db").as_posix()),
                gold_path=gold_path,
            )
            app = create_app(settings)
            status, payload = request(app, "GET", "/health")
            app.state.engine.dispose()
        self.assertEqual(status, 200)
        self.assertEqual(payload["configured_ai_provider"], "remote_medgemma")
        self.assertEqual(payload["active_provider"], "remote_medgemma")
        self.assertTrue(payload["remote_provider_reachable"])
        self.assertTrue(payload["is_real_llm"])

    def test_report_and_chat_use_remote_provider_metadata(self):
        requests.Session.request = fake_remote_request
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gold_path = root / "data" / "gold" / "report_context"
            gold_path.mkdir(parents=True)
            case = {
                "patient_id": "PAT-remote",
                "order_id": "ORD-remote",
                "specimen_id": "SPC-remote",
                "results_count": 1,
                "abnormal_results_count": 1,
                "normal_results_count": 0,
                "unknown_flag_results_count": 0,
                "validation_status_summary": "FINAL",
                "status": "READY_FOR_AI",
                "context_hash": "hash-remote",
                "results": [{"test_name": "Glucose", "abnormal_flag": "H"}],
            }
            with (gold_path / "context.jsonl").open("w", encoding="utf-8") as output:
                output.write(json.dumps(case) + "\n")

            settings = RemoteSettings(
                database_url="sqlite:///{}".format((root / "app_state" / "test.db").as_posix()),
                gold_path=gold_path,
            )
            app = create_app(settings)
            status, report = request(
                app,
                "POST",
                "/reports/generate",
                body={"patient_id": "PAT-remote", "order_id": "ORD-remote", "specimen_id": "SPC-remote"},
            )
            self.assertEqual(status, 200)
            self.assertEqual(report["provider_used"], "remote_medgemma")
            self.assertTrue(report["is_real_llm"])
            self.assertEqual(report["model_name"], "medgemma-4b-it")

            status, fetched = request(app, "GET", "/reports/{}".format(report["report_id"]))
            self.assertEqual(status, 200)
            self.assertEqual(fetched["latest_version"]["model_name"], "remote_medgemma:medgemma-4b-it")

            status, chat = request(
                app,
                "POST",
                "/reports/{}/chat".format(report["report_id"]),
                body={"question": "What is abnormal?"},
            )
            app.state.engine.dispose()

        self.assertEqual(status, 200)
        self.assertEqual(chat["provider_used"], "remote_medgemma")
        self.assertTrue(chat["is_real_llm"])


if __name__ == "__main__":
    unittest.main()
