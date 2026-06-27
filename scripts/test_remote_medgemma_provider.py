"""Strict smoke test for the remote MedGemma HTTP server."""

import json
import os
import sys

import requests


def _headers():
    api_key = os.getenv("MEDGEMMA_API_KEY", "")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer {}".format(api_key)
    return headers


def _require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    api_url = os.getenv("MEDGEMMA_API_URL", "http://localhost:9000").rstrip("/")
    timeout = int(os.getenv("MEDGEMMA_TIMEOUT_SECONDS", "180"))
    sample_context = {
        "patient_id": "PAT-sample",
        "order_id": "ORD-sample",
        "specimen_id": "SPC-sample",
        "results_count": 2,
        "abnormal_results_count": 1,
        "normal_results_count": 1,
        "unknown_flag_results_count": 0,
        "validation_status_summary": "FINAL",
        "context_hash": "sample-context-hash",
        "results": [
            {
                "test_name": "Glucose",
                "loinc_code": "2345-7",
                "value_raw": "160",
                "value_numeric": 160.0,
                "unit": "mg/dL",
                "reference_range": "70-110",
                "abnormal_flag": "H",
                "validation_status": "FINAL",
                "result_datetime": "2026-01-01T10:00:00Z",
            }
        ],
    }

    health = requests.get("{}/health".format(api_url), headers=_headers(), timeout=min(15, timeout))
    health.raise_for_status()
    health_payload = health.json()
    _require(health_payload.get("provider") == "remote_medgemma", "Health response is not remote_medgemma.")
    _require(health_payload.get("is_real_llm") is True, "Health response did not confirm is_real_llm=true.")

    response = requests.post(
        "{}/generate-report".format(api_url),
        headers=_headers(),
        timeout=timeout,
        json={
            "context": sample_context,
            "instructions": "Generate a structured AI draft biological report using only the provided context.",
        },
    )
    response.raise_for_status()
    payload = response.json()
    _require(payload.get("provider") == "remote_medgemma", "Generate response is not remote_medgemma.")
    _require(payload.get("is_real_llm") is True, "Generate response did not confirm is_real_llm=true.")
    _require(payload.get("model_name"), "Generate response did not include model_name.")
    _require(payload.get("report_text"), "Generate response did not include report_text.")

    print("Remote MedGemma provider test passed.")
    print("Provider: {}".format(payload.get("provider")))
    print("Model: {}".format(payload.get("model_name")))
    print("Report preview:")
    print(payload.get("report_text")[:1000])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Remote MedGemma provider test failed: {}".format(exc), file=sys.stderr)
        sys.exit(1)
