"""Strict full-app proof that the local AI backend used real remote MedGemma."""

import os
import sys

import requests


def _require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    backend_url = os.getenv("AI_BACKEND_URL", "http://127.0.0.1:8001").rstrip("/")
    timeout = int(os.getenv("MEDGEMMA_TIMEOUT_SECONDS", "180"))

    health = requests.get("{}/health".format(backend_url), timeout=15)
    health.raise_for_status()
    health_payload = health.json()
    _require(
        health_payload.get("configured_ai_provider") == "remote_medgemma",
        "AI backend is not configured with AI_PROVIDER=remote_medgemma.",
    )
    _require(
        health_payload.get("active_provider") == "remote_medgemma",
        "AI backend active provider is not remote_medgemma.",
    )
    _require(health_payload.get("require_real_llm") is True, "REQUIRE_REAL_LLM is not true.")
    _require(health_payload.get("is_real_llm") is True, "AI backend health did not confirm real LLM.")
    health_model_name = health_payload.get("model_name")

    cases = requests.get("{}/cases".format(backend_url), timeout=30)
    cases.raise_for_status()
    case_list = cases.json()
    _require(case_list, "No Gold cases are available. Run the PySpark pipeline first.")
    case = case_list[0]

    report_response = requests.post(
        "{}/reports/generate".format(backend_url),
        timeout=timeout,
        json={
            "patient_id": case["patient_id"],
            "order_id": case["order_id"],
            "specimen_id": case.get("specimen_id"),
        },
    )
    report_response.raise_for_status()
    report = report_response.json()
    _require(report.get("provider_used") == "remote_medgemma", "Report generation did not use remote_medgemma.")
    _require(report.get("is_real_llm") is True, "Report generation did not confirm is_real_llm=true.")
    _require(
        "medgemma" in report.get("model_name", "").lower()
        or report.get("model_name") == health_model_name,
        "Model name does not match the remote real-LLM health response.",
    )

    chat_response = requests.post(
        "{}/reports/{}/chat".format(backend_url, report["report_id"]),
        timeout=timeout,
        json={"question": "Summarize the abnormal findings for the biologist."},
    )
    chat_response.raise_for_status()
    chat = chat_response.json()
    _require(chat.get("provider_used") == "remote_medgemma", "Chat did not use remote_medgemma.")
    _require(chat.get("is_real_llm") is True, "Chat did not confirm is_real_llm=true.")

    print("Full local app real-LLM test passed.")
    print("Report ID: {}".format(report["report_id"]))
    print("Model: {}".format(report["model_name"]))
    print("Provider used: {}".format(report["provider_used"]))
    print("\nReport preview:\n{}".format(report["report_text"][:1000]))
    print("\nChat answer:\n{}".format(chat["answer"]))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Full app real-LLM test failed: {}".format(exc), file=sys.stderr)
        sys.exit(1)
