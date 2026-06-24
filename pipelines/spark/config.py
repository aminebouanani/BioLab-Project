"""Configuration for the local PySpark medallion pipeline."""

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


class PipelineConfig:
    """Path and Spark settings for local medallion processing."""

    def __init__(self):
        load_dotenv()
        self.kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.spark_master = os.getenv("SPARK_MASTER", "local[*]")
        self.data_lake_root = resolve_path(os.getenv("DATA_LAKE_ROOT", "data"))
        self.bronze_path = resolve_path(os.getenv("BRONZE_PATH", "data/bronze/glims_events"))
        self.silver_path = resolve_path(os.getenv("SILVER_PATH", "data/silver/lab_results"))
        self.gold_report_context_path = resolve_path(
            os.getenv("GOLD_REPORT_CONTEXT_PATH", "data/gold/report_context")
        )
        self.gold_dashboard_kpis_path = resolve_path(
            os.getenv("GOLD_DASHBOARD_KPIS_PATH", "data/gold/dashboard_kpis")
        )
        self.full_jsonl_path = resolve_path("data/bronze/glims_lab_results.jsonl")
        self.sample_jsonl_path = resolve_path("samples/glims_lab_results_sample.jsonl")
        self.reference_ranges_path = resolve_path("config/lab_reference_ranges.yml")


def create_spark_session(config):
    from pyspark.sql import SparkSession

    return (
        SparkSession.builder.appName("BioLabLocalMedallionPipeline")
        .master(config.spark_master)
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
