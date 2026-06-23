"""Configuration for local Kafka/Redpanda streaming."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path=None):
    """Load simple KEY=value pairs without requiring python-dotenv."""
    env_path = path or PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


class KafkaSettings:
    def __init__(self):
        load_dotenv()
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.enabled = env_bool("KAFKA_ENABLED", False)

    def as_dict(self):
        return {
            "bootstrap_servers": self.bootstrap_servers,
            "enabled": self.enabled,
        }
