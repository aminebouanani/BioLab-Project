"""Run the full local pre-Azure backend validation flow."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = PROJECT_ROOT / "demo" / "output" / "pre_azure_validation_summary.json"
QUESTION = "Which results are abnormal and what should the biologist pay attention to?"


class ValidationError(Exception):
    pass


def _bool_env(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _require(condition, message):
    if not condition:
        raise ValidationError(message)


def _request(method, url, timeout=180, **kwargs):
    response = requests.request(method, url, timeout=timeout, **kwargs)
    response.raise_for_status()
    return response


def _check_real_llm_health(health: Dict[str, Any], require_real_llm: bool):
    if not require_real_llm:
        return
    _require(health.get("active_provider") == "remote_medgemma", "AI backend active_provider is not remote_medgemma.")
    _require(health.get("configured_ai_provider") == "remote_medgemma", "AI backend is not configured for remote_medgemma.")
    _require(health.get("require_real_llm") is True, "AI backend health does not show require_real_llm=true.")
    _require(health.get("is_real_llm") is True, "AI backend did not confirm is_real_llm=true.")
    _require(health.get("model_name"), "AI backend health is missing model_name.")


def _check_real_llm_response(payload: Dict[str, Any], require_real_llm: bool, label: str):
    if not require_real_llm:
        return
    _require(payload.get("provider_used") == "remote_medgemma", "{} did not use remote_medgemma.".format(label))
    _require(payload.get("is_real_llm") is True, "{} did not confirm is_real_llm=true.".format(label))
    _require(payload.get("model_name"), "{} response is missing model_name.".format(label))


def run_validation(backend_url=None, summary_path=SUMMARY_PATH):
    backend_url = (backend_url or os.getenv("AI_BACKEND_URL", "http://127.0.0.1:8001")).rstrip("/")
    require_real_llm = _bool_env("REQUIRE_REAL_LLM", False)
    timeout = int(os.getenv("MEDGEMMA_TIMEOUT_SECONDS", "180"))
    steps: List[Dict[str, str]] = []

    def step(name, status="PASS", details=""):
        steps.append({"step": name, "status": status, "details": details})

    try:
        health = _request("GET", "{}/health".format(backend_url), timeout=15).json()
        step("AI backend health", details="active_provider={}, is_real_llm={}".format(health.get("active_provider"), health.get("is_real_llm")))

        _check_real_llm_health(health, require_real_llm)
        step("Real LLM strict mode check", details="require_real_llm={}".format(require_real_llm))

        cases = _request("GET", "{}/cases".format(backend_url), timeout=30).json()
        _require(cases, "No Gold cases returned. Run the PySpark pipeline first.")
        case = next((item for item in cases if item.get("status") == "READY_FOR_AI"), cases[0])
        step("Gold cases loaded", details="cases_count={}".format(len(cases)))

        report = _request(
            "POST",
            "{}/reports/generate".format(backend_url),
            timeout=timeout,
            json={
                "patient_id": case["patient_id"],
                "order_id": case["order_id"],
                "specimen_id": case.get("specimen_id"),
            },
        ).json()
        _require(report.get("report_id"), "Report generation did not return report_id.")
        _require(report.get("report_text"), "Report generation did not return report_text.")
        _check_real_llm_response(report, require_real_llm, "Report generation")
        step("AI report generated", details="report_id={}".format(report.get("report_id")))

        chat = _request(
            "POST",
            "{}/reports/{}/chat".format(backend_url, report["report_id"]),
            timeout=timeout,
            json={"question": QUESTION},
        ).json()
        _require(chat.get("answer"), "Chat response did not include answer.")
        _check_real_llm_response(chat, require_real_llm, "Chat")
        step("Chatbot answered", details="answer_length={}".format(len(chat.get("answer", ""))))

        outdated = _request("POST", "{}/reports/{}/check-outdated".format(backend_url, report["report_id"]), timeout=30).json()
        _require(outdated.get("is_outdated") is False, "Report is unexpectedly outdated.")
        step("Outdated check", details="is_outdated=false")

        validated = _request(
            "POST",
            "{}/reports/{}/validate".format(backend_url, report["report_id"]),
            timeout=30,
            json={"comment": "Validated during pre-Azure end-to-end test."},
        ).json()
        _require(validated.get("status") == "BIOLOGIST_VALIDATED", "Report validation did not return BIOLOGIST_VALIDATED.")
        step("Report validated", details="status=BIOLOGIST_VALIDATED")

        pdf = _request("POST", "{}/reports/{}/generate-pdf".format(backend_url, report["report_id"]), timeout=60).json()
        _require(pdf.get("export_id"), "PDF export did not return export_id.")
        _require(pdf.get("pdf_filename"), "PDF export did not return pdf_filename.")
        _require(pdf.get("export_status") == "GENERATED", "PDF export status is not GENERATED.")
        _require(pdf.get("download_url"), "PDF export did not return download_url.")
        step("Final PDF generated", details="export_id={}".format(pdf.get("export_id")))

        pdf_response = _request("GET", "{}/reports/{}/pdf/download".format(backend_url, report["report_id"]), timeout=60)
        content_type = pdf_response.headers.get("content-type", "")
        _require("application/pdf" in content_type, "PDF download content type is not application/pdf: {}".format(content_type))
        _require(len(pdf_response.content) > 0, "Downloaded PDF is empty.")
        step("PDF downloaded", details="bytes={}".format(len(pdf_response.content)))

        summary = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "result": "PASS",
            "backend_url": backend_url,
            "selected_patient_id": case.get("patient_id"),
            "order_id": case.get("order_id"),
            "specimen_id": case.get("specimen_id"),
            "report_id": report.get("report_id"),
            "model_name": report.get("model_name"),
            "provider_used": report.get("provider_used"),
            "is_real_llm": report.get("is_real_llm"),
            "pdf_export_id": pdf.get("export_id"),
            "pdf_filename": pdf.get("pdf_filename"),
            "steps": steps,
        }
        save_summary(summary, summary_path)
        return summary
    except Exception as exc:
        steps.append({"step": "Validation failed", "status": "FAIL", "details": str(exc)})
        summary = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "result": "FAIL",
            "backend_url": backend_url,
            "error": str(exc),
            "steps": steps,
        }
        save_summary(summary, summary_path)
        raise


def save_summary(summary, summary_path=SUMMARY_PATH):
    summary_path = Path(summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def main():
    try:
        summary = run_validation()
        print("PRE-AZURE VALIDATION PASSED")
        print("Report ID: {}".format(summary["report_id"]))
        print("Provider used: {}".format(summary["provider_used"]))
        print("Model name: {}".format(summary["model_name"]))
        print("PDF: {}".format(summary["pdf_filename"]))
        print("Summary: {}".format(SUMMARY_PATH))
    except Exception as exc:
        print("PRE-AZURE VALIDATION FAILED: {}".format(exc), file=sys.stderr)
        print("Summary: {}".format(SUMMARY_PATH), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
