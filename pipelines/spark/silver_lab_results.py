"""Silver transformations for cleaned GLIMS lab results."""

import logging

from pyspark.sql import Window, functions as F
from pyspark.sql.types import DoubleType, StringType

from pipelines.spark.utils import (
    abnormal_flag_for_value,
    load_reference_ranges,
    parse_numeric_value,
    read_medallion_dataframe,
    write_dataframe,
)

LOGGER = logging.getLogger(__name__)

LAB_RESULT_EVENT_TYPES = ["LAB_RESULT_CREATED", "LAB_RESULT_UPDATED", "LAB_RESULT"]


def build_silver_lab_results(spark, config, bronze_df=None):
    ranges = load_reference_ranges(config.reference_ranges_path)
    parse_numeric_udf = F.udf(parse_numeric_value, DoubleType())
    flag_udf = F.udf(lambda loinc, value: abnormal_flag_for_value(loinc, value, ranges), StringType())

    bronze = bronze_df if bronze_df is not None else read_medallion_dataframe(spark, config.bronze_path)
    normalized = (
        bronze.withColumn("event_type", F.upper(F.trim(F.col("event_type"))))
        .withColumn("validation_status", F.upper(F.trim(F.col("validation_status"))))
        .withColumn("result_datetime", F.to_timestamp("result_datetime"))
        .withColumn("modified_at", F.coalesce(F.to_timestamp("modified_at"), F.col("result_datetime")))
        .withColumn(
            "result_id",
            F.when(F.col("result_id").isNotNull() & (F.length(F.trim(F.col("result_id"))) > 0), F.col("result_id")).otherwise(
                F.concat(
                    F.lit("RES-"),
                    F.sha2(
                        F.concat_ws(
                            "|",
                            F.col("patient_id"),
                            F.col("order_id"),
                            F.col("specimen_id"),
                            F.col("test_code"),
                            F.col("result_datetime").cast("string"),
                        ),
                        256,
                    ),
                )
            ),
        )
        .withColumn("value_raw", F.col("value").cast("string"))
        .withColumn("value_numeric", parse_numeric_udf(F.col("value")))
        .withColumn(
            "value_text",
            F.when(F.col("value_numeric").isNull(), F.col("value").cast("string")).otherwise(F.lit(None).cast("string")),
        )
        .withColumn("abnormal_flag", flag_udf(F.coalesce(F.col("loinc_code"), F.col("test_code")), F.col("value_numeric")))
    )

    required = ["patient_id", "order_id", "specimen_id", "result_id"]
    filtered = normalized.filter(F.col("event_type").isin(LAB_RESULT_EVENT_TYPES))
    for column in required:
        filtered = filtered.filter(F.col(column).isNotNull() & (F.length(F.trim(F.col(column))) > 0))

    deduplicated = filtered.dropDuplicates(["event_id"])
    latest_window = Window.partitionBy("result_id").orderBy(F.col("modified_at").desc_nulls_last())
    latest = (
        deduplicated.withColumn("_latest_rank", F.row_number().over(latest_window))
        .filter(F.col("_latest_rank") == 1)
        .drop("_latest_rank")
        .withColumn("is_latest", F.lit(True))
        .withColumn("cleaned_at", F.current_timestamp())
    )
    return latest


def write_silver_lab_results(spark, config):
    df = build_silver_lab_results(spark, config)
    records = df.count()
    output_format = write_dataframe(df, config.silver_path)
    LOGGER.info("Wrote %d silver lab-result records to %s as %s", records, config.silver_path, output_format)
    return {"records": records, "path": str(config.silver_path), "format": output_format}
