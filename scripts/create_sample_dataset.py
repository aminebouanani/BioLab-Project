"""Create a small, committable sample from the local bronze GLIMS dataset."""

import json
import sys
from pathlib import Path
from typing import TextIO

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = PROJECT_ROOT / "data" / "bronze" / "glims_lab_results.jsonl"
SAMPLE_PATH = PROJECT_ROOT / "samples" / "glims_lab_results_sample.jsonl"
SAMPLE_SIZE = 100


def _warn(message: str) -> None:
    print("Warning: {}".format(message), file=sys.stderr)


def write_sample(source_path: Path, sample_path: Path, limit: int = SAMPLE_SIZE) -> int:
    """Write the first valid JSON-object events from source to the sample file."""
    if not source_path.is_file():
        raise FileNotFoundError(
            "Full bronze dataset not found at {}. Generate it first with "
            "'python -m glims_adapter.main'.".format(source_path)
        )

    sample_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0

    with source_path.open("r", encoding="utf-8") as source_file, sample_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as sample_file:
        _copy_valid_events(source_file, sample_file, limit)

    # Count the output after closing it so the reported number always reflects disk.
    with sample_path.open("r", encoding="utf-8") as sample_file:
        event_count = sum(1 for _ in sample_file)

    if event_count < limit:
        _warn("only {} valid events were available; requested {}".format(event_count, limit))
    return event_count


def _copy_valid_events(source_file: TextIO, sample_file: TextIO, limit: int) -> None:
    written = 0
    for line_number, line in enumerate(source_file, start=1):
        if written >= limit:
            break
        if not line.strip():
            _warn("skipping blank source line {}".format(line_number))
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            _warn("skipping invalid JSON on source line {}: {}".format(line_number, exc))
            continue
        if not isinstance(event, dict):
            _warn("skipping non-object JSON on source line {}".format(line_number))
            continue

        sample_file.write(json.dumps(event, ensure_ascii=True, separators=(",", ":")) + "\n")
        written += 1


def main() -> None:
    try:
        count = write_sample(SOURCE_PATH, SAMPLE_PATH)
    except (OSError, ValueError) as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        sys.exit(1)

    print("Success: wrote {} valid events to {}".format(count, SAMPLE_PATH))


if __name__ == "__main__":
    main()
