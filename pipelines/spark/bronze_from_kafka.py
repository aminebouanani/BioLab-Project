"""Bronze ingestion from Kafka or local JSONL fallback."""

import logging
from pathlib import Path

from pyspark.sql import functions as F

from pipelines.spark.schemas import GLIMS_EVENT_SCHEMA
from pipelines.spark.utils import write_dataframe
from streaming.topics import GLIMS_RESULT_TOPIC

LOGGER = logging.getLogger(__name__)


def _with_bronze_metadata(df):
    return df.withColumn("ingestion_timestamp", F.current_timestamp())


def _source_jsonl_path(config) -> Path:
    if config.full_jsonl_path.is_file():
        return config.full_jsonl_path
    if config.sample_jsonl_path.is_file():
        LOGGER.warning("Full JSONL missing; using sample dataset %s", config.sample_jsonl_path)
        return config.sample_jsonl_path
    raise FileNotFoundError("No JSONL source found at {} or {}".format(config.full_jsonl_path, config.sample_jsonl_path))


def read_jsonl_events(spark, config):
    source_path = _source_jsonl_path(config)
    df = spark.read.schema(GLIMS_EVENT_SCHEMA).json(str(source_path))
    return (
        _with_bronze_metadata(df)
        .withColumn("kafka_topic", F.lit(None).cast("string"))
        .withColumn("kafka_partition", F.lit(None).cast("integer"))
        .withColumn("kafka_offset", F.lit(None).cast("long"))
    )


def read_kafka_events(spark, config):
    kafka_df = (
        spark.read.format("kafka")
        .option("kafka.bootstrap.servers", config.kafka_bootstrap_servers)
        .option("subscribe", GLIMS_RESULT_TOPIC)
        .option("startingOffsets", "earliest")
        .option("endingOffsets", "latest")
        .load()
    )
    parsed = kafka_df.select(
        F.from_json(F.col("value").cast("string"), GLIMS_EVENT_SCHEMA).alias("event"),
        F.col("topic").alias("kafka_topic"),
        F.col("partition").alias("kafka_partition"),
        F.col("offset").alias("kafka_offset"),
    )
    return _with_bronze_metadata(parsed.select("event.*", "kafka_topic", "kafka_partition", "kafka_offset"))


def build_bronze_events(spark, config, source):
    if source == "kafka":
        try:
            return read_kafka_events(spark, config)
        except Exception as exc:
            LOGGER.warning("Kafka read failed, falling back to JSONL development source: %s", exc)
            return read_jsonl_events(spark, config)
    if source == "jsonl":
        return read_jsonl_events(spark, config)
    raise ValueError("Unsupported source: {}".format(source))


def write_bronze_events(spark, config, source):
    df = build_bronze_events(spark, config, source)
    records = df.count()
    output_format = write_dataframe(df, config.bronze_path)
    LOGGER.info("Wrote %d bronze records to %s as %s", records, config.bronze_path, output_format)
    return {"records": records, "path": str(config.bronze_path), "format": output_format}
