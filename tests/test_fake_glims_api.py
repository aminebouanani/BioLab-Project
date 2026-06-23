"""Smoke tests for the fake GLIMS FastAPI service."""

import asyncio
import json
import os
import unittest
from urllib.parse import urlencode

os.environ["KAFKA_ENABLED"] = "false"

from fake_glims_api.app.main import app


def request(method, path, params=None):
    """Exercise the FastAPI app directly through ASGI without test dependencies."""
    messages = []
    query_string = urlencode(params or {}).encode("ascii")
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query_string,
        "headers": [(b"host", b"testserver")],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.get_event_loop().run_until_complete(app(scope, receive, send))

    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return status, json.loads(body.decode("utf-8"))


class FakeGlimsApiTests(unittest.TestCase):
    def test_root_returns_api_info(self):
        status, payload = request("GET", "/")

        self.assertEqual(status, 200)
        self.assertEqual(payload["service_name"], "fake-glims-api")
        self.assertEqual(payload["docs_url"], "/docs")

    def test_health_returns_200(self):
        status, payload = request("GET", "/health")

        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertGreater(payload["loaded_events"], 0)

    def test_patients_returns_a_list(self):
        status, payload = request("GET", "/patients")

        self.assertEqual(status, 200)
        self.assertIsInstance(payload, list)

    def test_results_returns_events(self):
        status, payload = request("GET", "/results", params={"limit": 5})

        self.assertEqual(status, 200)
        self.assertGreater(len(payload), 0)
        self.assertIn("result_id", payload[0])
        self.assertIn("modified_at", payload[0])

    def test_stream_patient_has_kafka_disabled(self):
        _, patients = request("GET", "/patients")
        patient_id = patients[0]["patient_id"]

        status, payload = request("POST", "/stream/patient/{}".format(patient_id))

        self.assertEqual(status, 200)
        self.assertFalse(payload["kafka_publishing_enabled"])
        self.assertEqual(payload["patient_id"], patient_id)
        self.assertEqual(payload["events_count"], len(payload["events"]))
        self.assertEqual(payload["published_count"], 0)

    def test_stream_all_limit_has_kafka_disabled(self):
        status, payload = request("POST", "/stream/all", params={"limit": 10})

        self.assertEqual(status, 200)
        self.assertFalse(payload["kafka_publishing_enabled"])
        self.assertEqual(payload["events_count"], 10)
        self.assertEqual(payload["published_count"], 0)
        self.assertEqual(payload["topics_used"], [])


if __name__ == "__main__":
    unittest.main()
