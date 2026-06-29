"""Reset local demo state safely."""

import argparse
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _inside_project(path):
    resolved = Path(path).resolve()
    root = PROJECT_ROOT.resolve()
    return resolved == root or root in resolved.parents


def _remove_path(path):
    path = Path(path)
    if not _inside_project(path):
        raise RuntimeError("Refusing to delete path outside project: {}".format(path))
    if not path.exists():
        return False
    if path.is_dir():
        shutil.rmtree(str(path))
    else:
        path.unlink()
    return True


def reset_state(include_lakehouse=False):
    targets = [
        PROJECT_ROOT / "app_state" / "biolab_local.db",
        PROJECT_ROOT / "app_state" / "generated_reports",
        PROJECT_ROOT / "demo" / "output",
    ]
    if include_lakehouse:
        targets.extend(
            [
                PROJECT_ROOT / "data" / "bronze",
                PROJECT_ROOT / "data" / "silver",
                PROJECT_ROOT / "data" / "gold",
            ]
        )
    removed = []
    for target in targets:
        if _remove_path(target):
            removed.append(str(target))
    return removed


def main():
    parser = argparse.ArgumentParser(description="Reset local BioLab demo state.")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt.")
    parser.add_argument("--include-lakehouse", action="store_true", help="Also remove data/bronze, data/silver, and data/gold.")
    args = parser.parse_args()

    if not args.yes:
        print("This will delete local demo database/PDF/output state.")
        if args.include_lakehouse:
            print("It will also delete local data/bronze, data/silver, and data/gold outputs.")
        answer = input("Type RESET to continue: ")
        if answer != "RESET":
            print("Cancelled.")
            return

    removed = reset_state(include_lakehouse=args.include_lakehouse)
    if not removed:
        print("Nothing to reset.")
    else:
        print("Removed:")
        for item in removed:
            print("- {}".format(item))


if __name__ == "__main__":
    main()
