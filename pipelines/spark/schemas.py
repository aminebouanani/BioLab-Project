"""Spark schemas for GLIMS-like lab result events."""

from pyspark.sql.types import StringType, StructField, StructType


GLIMS_EVENT_SCHEMA = StructType(
    [
        StructField("event_id", StringType(), True),
        StructField("source_system", StringType(), True),
        StructField("origin_source", StringType(), True),
        StructField("event_type", StringType(), True),
        StructField("patient_id", StringType(), True),
        StructField("order_id", StringType(), True),
        StructField("specimen_id", StringType(), True),
        StructField("test_code", StringType(), True),
        StructField("loinc_code", StringType(), True),
        StructField("test_name", StringType(), True),
        StructField("value", StringType(), True),
        StructField("unit", StringType(), True),
        StructField("reference_range", StringType(), True),
        StructField("abnormal_flag", StringType(), True),
        StructField("validation_status", StringType(), True),
        StructField("result_datetime", StringType(), True),
        StructField("result_id", StringType(), True),
        StructField("modified_at", StringType(), True),
    ]
)
