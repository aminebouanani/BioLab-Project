"""Check local demo services before running the pre-Azure validation."""

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import List

import requests


TOPICS = [
    "glims.patient",
    "glims.order",
    "glims.specimen",
    "glims.result",
    "glims.validation",
]


@dataclass
class ServiceCheck:
    service: str
    check: str
    status: str
    details: str

    @property
    def ok(self):
        return self.status == "OK"


def _get_json(url, timeout=5):
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text[:200]}


def check_http_service(name, url, expected=None):
    try:
        payload = _get_json(url)
        if expected:
            for key, value in expected.items():
                if payload.get(key) != value:
                    return ServiceCheck(name, url, "FAIL", "{} expected {}, got {}".format(key, value, payload.get(key)))
        return ServiceCheck(name, url, "OK", _summarize_payload(payload))
    except Exception as exc:
        return ServiceCheck(name, url, "FAIL", str(exc))


def check_dashboard(url="http://localhost:5173"):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return ServiceCheck("React Dashboard", url, "OK", "HTTP {}".format(response.status_code))
    except Exception as exc:
        return ServiceCheck("React Dashboard", url, "FAIL", str(exc))


def check_redpanda():
    docker_check = _check_redpanda_docker()
    if docker_check.ok:
        return docker_check
    kafka_check = _check_kafka_topics()
    if kafka_check.ok:
        return kafka_check
    return ServiceCheck(
        "Redpanda/Kafka",
        "docker ps or Kafka topic metadata",
        "FAIL",
        "Docker check: {}; Kafka check: {}".format(docker_check.details, kafka_check.details),
    )


def _check_redpanda_docker():
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return ServiceCheck("Redpanda/Kafka", "docker ps", "FAIL", result.stderr.strip() or "docker ps failed")
        names = result.stdout.splitlines()
        matching = [name for name in names if "redpanda" in name.lower()]
        if matching:
            return ServiceCheck("Redpanda/Kafka", "docker ps", "OK", "Running container(s): {}".format(", ".join(matching)))
        return ServiceCheck("Redpanda/Kafka", "docker ps", "FAIL", "No Redpanda container found")
    except Exception as exc:
        return ServiceCheck("Redpanda/Kafka", "docker ps", "FAIL", str(exc))


def _check_kafka_topics():
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    try:
        from confluent_kafka.admin import AdminClient
    except Exception as exc:
        return ServiceCheck("Redpanda/Kafka", "Kafka topics", "FAIL", "confluent-kafka unavailable: {}".format(exc))
    try:
        admin = AdminClient({"bootstrap.servers": bootstrap})
        metadata = admin.list_topics(timeout=5)
        existing = set(metadata.topics.keys())
        missing = [topic for topic in TOPICS if topic not in existing]
        if missing:
            return ServiceCheck("Redpanda/Kafka", "Kafka topics", "FAIL", "Missing topics: {}".format(", ".join(missing)))
        return ServiceCheck("Redpanda/Kafka", "Kafka topics", "OK", "Topics present on {}".format(bootstrap))
    except Exception as exc:
        return ServiceCheck("Redpanda/Kafka", "Kafka topics", "FAIL", str(exc))


def _summarize_payload(payload):
    if not isinstance(payload, dict):
        return str(payload)[:200]
    parts = []
    for key in ("service", "service_name", "status", "database_status", "active_provider", "is_real_llm", "provider_ready"):
        if key in payload:
            parts.append("{}={}".format(key, payload.get(key)))
    return ", ".join(parts) or str(payload)[:200]


def run_checks():
    medgemma_url = os.getenv("MEDGEMMA_API_URL", "http://localhost:9000").rstrip("/")
    checks = [
        check_http_service("Fake GLIMS API", "http://127.0.0.1:8000/health"),
        check_http_service("AI Backend", "http://127.0.0.1:8001/health"),
        check_dashboard(),
        check_http_service("Remote MedGemma", "{}/health".format(medgemma_url), {"provider": "remote_medgemma"}),
        check_redpanda(),
    ]
    return checks


def print_table(checks: List[ServiceCheck]):
    headers = ("Service", "URL/Check", "Status", "Details")
    rows = [(item.service, item.check, item.status, item.details) for item in checks]
    widths = [
        max(len(str(row[index])) for row in rows + [headers])
        for index in range(4)
    ]
    line = " | ".join(headers[index].ljust(widths[index]) for index in range(4))
    print(line)
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(str(row[index]).ljust(widths[index]) for index in range(4)))


def main():
    checks = run_checks()
    print_table(checks)
    if not all(item.ok for item in checks):
        print("\nOne or more required demo services are unavailable.", file=sys.stderr)
        sys.exit(1)
    print("\nAll required demo services are available.")


if __name__ == "__main__":
    main()
