"""Gold report context and dashboard KPI builders."""

import logging

from pyspark.sql import functions as F

from pipelines.spark.utils import read_medallion_dataframe, write_dataframe

LOGGER = logging.getLogger(__name__)


def build_gold_report_context(spark, config, silver_df=None):
    silver = silver_df if silver_df is not None else read_medallion_dataframe(spark, config.silver_path)
    latest = silver.filter(F.col("is_latest") == True)
    result_struct = F.struct(
        "result_id",
        "test_code",
        "loinc_code",
        "test_name",
        "value_raw",
        "value_numeric",
        "value_text",
        "unit",
        "reference_range",
        "abnormal_flag",
        "validation_status",
        "result_datetime",
        "modified_at",
    )
    results_array = F.array_sort(F.collect_list(result_struct))

    grouped = latest.groupBy("patient_id", "order_id", "specimen_id").agg(
        F.count("*").alias("results_count"),
        F.sum(F.when(F.col("abnormal_flag").isin("H", "L"), 1).otherwise(0)).cast("long").alias("abnormal_results_count"),
        F.sum(F.when(F.col("abnormal_flag") == "N", 1).otherwise(0)).cast("long").alias("normal_results_count"),
        F.sum(F.when(F.col("abnormal_flag") == "UNKNOWN", 1).otherwise(0)).cast("long").alias("unknown_flag_results_count"),
        F.min("result_datetime").alias("first_result_datetime"),
        F.max("result_datetime").alias("last_result_datetime"),
        F.concat_ws(",", F.array_sort(F.collect_set("validation_status"))).alias("validation_status_summary"),
        results_array.alias("results"),
    )

    hash_results = F.transform(
        F.col("results"),
        lambda item: F.struct(
            item["result_id"].alias("result_id"),
            item["test_code"].alias("test_code"),
            item["value_raw"].alias("value_raw"),
            item["unit"].alias("unit"),
            item["abnormal_flag"].alias("abnormal_flag"),
            item["validation_status"].alias("validation_status"),
            item["modified_at"].cast("string").alias("modified_at"),
        ),
    )
    return (
        grouped.withColumn(
            "status",
            F.when(F.col("results_count") > 0, F.lit("READY_FOR_AI")).otherwise(F.lit("INCOMPLETE")),
        )
        .withColumn(
            "context_hash",
            F.sha2(
                F.concat_ws(
                    "|",
                    F.col("patient_id"),
                    F.col("order_id"),
                    F.col("specimen_id"),
                    F.to_json(hash_results),
                ),
                256,
            ),
        )
        .withColumn("generated_at", F.current_timestamp())
    )


def build_gold_dashboard_kpis(spark, config, silver_df=None, report_context_df=None):
    silver = silver_df if silver_df is not None else read_medallion_dataframe(spark, config.silver_path)
    context = (
        report_context_df
        if report_context_df is not None
        else read_medallion_dataframe(spark, config.gold_report_context_path)
    )
    metrics = {
        "total_patients": silver.select("patient_id").distinct().count(),
        "total_orders": silver.select("order_id").distinct().count(),
        "total_results": silver.select("result_id").distinct().count(),
        "ready_for_ai_cases": context.filter(F.col("status") == "READY_FOR_AI").count(),
        "abnormal_results_count": silver.filter(F.col("abnormal_flag").isin("H", "L")).count(),
    }
    return spark.createDataFrame([metrics]).withColumn("generated_at", F.current_timestamp())


def write_gold_outputs(spark, config):
    silver = read_medallion_dataframe(spark, config.silver_path)
    report_context = build_gold_report_context(spark, config, silver)
    report_records = report_context.count()
    report_format = write_dataframe(report_context, config.gold_report_context_path)

    dashboard_kpis = build_gold_dashboard_kpis(spark, config, silver, report_context)
    kpi_records = dashboard_kpis.count()
    kpi_format = write_dataframe(dashboard_kpis, config.gold_dashboard_kpis_path)

    LOGGER.info("Wrote %d gold report contexts to %s", report_records, config.gold_report_context_path)
    LOGGER.info("Wrote %d gold KPI rows to %s", kpi_records, config.gold_dashboard_kpis_path)
    return {
        "report_context": {
            "records": report_records,
            "path": str(config.gold_report_context_path),
            "format": report_format,
        },
        "dashboard_kpis": {
            "records": kpi_records,
            "path": str(config.gold_dashboard_kpis_path),
            "format": kpi_format,
        },
    }
