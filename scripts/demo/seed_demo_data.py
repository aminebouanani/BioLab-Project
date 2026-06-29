"""Ensure local Gold report context exists for demo runs."""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOLD_CONTEXT_PATH = PROJECT_ROOT / "data" / "gold" / "report_context"


def gold_context_has_data(path=GOLD_CONTEXT_PATH):
    path = Path(path)
    if not path.exists():
        return False
    patterns = ("*.parquet", "*.json", "*.jsonl")
    return any(any(path.glob(pattern)) for pattern in patterns)


def run_pipeline():
    command = [sys.executable, "-m", "pipelines.spark.run_local_pipeline", "--source", "jsonl"]
    return subprocess.run(command, cwd=str(PROJECT_ROOT), check=False)


def main():
    parser = argparse.ArgumentParser(description="Check or seed local Gold report context.")
    parser.add_argument("--run-pipeline", action="store_true", help="Run the local JSONL PySpark pipeline if Gold context is missing.")
    args = parser.parse_args()

    if gold_context_has_data():
        print("Gold report context is available: {}".format(GOLD_CONTEXT_PATH))
        return

    print("Gold report context is missing or empty: {}".format(GOLD_CONTEXT_PATH))
    if not args.run_pipeline:
        print("Run:")
        print("python -m pipelines.spark.run_local_pipeline --source jsonl")
        print("Or rerun this helper with:")
        print("python scripts/demo/seed_demo_data.py --run-pipeline")
        sys.exit(1)

    print("Running local PySpark pipeline in JSONL mode...")
    result = run_pipeline()
    if result.returncode != 0:
        print("Pipeline failed with exit code {}.".format(result.returncode), file=sys.stderr)
        sys.exit(result.returncode)
    if not gold_context_has_data():
        print("Pipeline completed but Gold report context is still missing.", file=sys.stderr)
        sys.exit(1)
    print("Gold report context is now available: {}".format(GOLD_CONTEXT_PATH))


if __name__ == "__main__":
    main()
