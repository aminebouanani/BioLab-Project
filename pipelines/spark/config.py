"""Configuration for the local PySpark medallion pipeline."""

import os
import re
import subprocess
import sys
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


def parse_java_major_version(version_output):
    match = re.search(r'version "([^"]+)"', version_output)
    if not match:
        return None
    version = match.group(1)
    if version.startswith("1."):
        return int(version.split(".")[1])
    return int(version.split(".")[0])


def java_major_version():
    try:
        completed = subprocess.run(
            ["java", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except OSError:
        return None
    return parse_java_major_version(completed.stderr or completed.stdout)


def ensure_local_spark_runtime():
    """Prepare Windows-friendly PySpark defaults and validate Java compatibility."""
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

    major = java_major_version()
    if major is None:
        raise RuntimeError(
            "Java was not found. Install Java 11 or 17 and make sure 'java -version' works."
        )
    if major > 17:
        raise RuntimeError(
            "Detected Java {}. This project uses PySpark 3.3 on Python 3.7, "
            "which requires Java 8, 11, or 17. Install Java 17, set JAVA_HOME "
            "to that JDK, update PATH, then rerun the pipeline.".format(major)
        )


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
        self.spark_extra_java_options = os.getenv(
            "SPARK_EXTRA_JAVA_OPTIONS",
            "-Djava.security.manager=allow",
        )


def create_spark_session(config):
    ensure_local_spark_runtime()
    from pyspark.sql import SparkSession

    return (
        SparkSession.builder.appName("BioLabLocalMedallionPipeline")
        .master(config.spark_master)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.extraJavaOptions", config.spark_extra_java_options)
        .config("spark.executor.extraJavaOptions", config.spark_extra_java_options)
        .getOrCreate()
    )
