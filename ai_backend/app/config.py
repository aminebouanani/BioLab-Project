"""Configuration for the local AI backend."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path=None):
    env_path = path or PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def resolve_path(value):
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def resolve_sqlite_url(value):
    if value == "sqlite:///:memory:":
        return value
    if not value.startswith("sqlite:///"):
        return value
    raw_path = value.replace("sqlite:///", "", 1)
    path = resolve_path(raw_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return "sqlite:///{}".format(path.as_posix())


class Settings:
    def __init__(self):
        load_dotenv()
        self.database_url = resolve_sqlite_url(
            os.getenv("AI_BACKEND_DATABASE_URL", "sqlite:///app_state/biolab_local.db")
        )
        self.data_lake_root = resolve_path(os.getenv("DATA_LAKE_ROOT", "data"))
        self.gold_report_context_path = resolve_path(
            os.getenv("GOLD_REPORT_CONTEXT_PATH", "data/gold/report_context")
        )
        self.ai_provider = os.getenv("AI_PROVIDER", "mock_medgemma")
