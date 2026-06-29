"""Print a human-readable summary from the pre-Azure validation JSON."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = PROJECT_ROOT / "demo" / "output" / "pre_azure_validation_summary.json"


def load_summary(path=SUMMARY_PATH):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError("Validation summary not found: {}".format(path))
    return json.loads(path.read_text(encoding="utf-8"))


def format_summary(summary):
    lines = [
        "BioLab Pre-Azure Validation Summary",
        "====================================",
        "Result: {}".format(summary.get("result", "UNKNOWN")),
        "Timestamp: {}".format(summary.get("timestamp", "")),
        "Case selected: patient_id={}, order_id={}, specimen_id={}".format(
            summary.get("selected_patient_id", ""),
            summary.get("order_id", ""),
            summary.get("specimen_id", ""),
        ),
        "AI provider used: {}".format(summary.get("provider_used", "")),
        "Model name: {}".format(summary.get("model_name", "")),
        "is_real_llm: {}".format(summary.get("is_real_llm", "")),
        "Report generated: {}".format(summary.get("report_id", "")),
        "PDF generated: {} ({})".format(summary.get("pdf_export_id", ""), summary.get("pdf_filename", "")),
        "",
        "Steps:",
    ]
    for step in summary.get("steps", []):
        lines.append("- [{status}] {step}: {details}".format(**step))
    return "\n".join(lines)


def main():
    try:
        summary = load_summary()
        print(format_summary(summary))
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        print("Run python scripts/demo/run_pre_azure_validation.py first.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
