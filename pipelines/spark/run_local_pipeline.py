"""CLI runner for the local PySpark medallion pipeline."""

import argparse
import logging

from pipelines.spark.bronze_from_kafka import write_bronze_events
from pipelines.spark.config import PipelineConfig, create_spark_session
from pipelines.spark.gold_report_context import write_gold_outputs
from pipelines.spark.silver_lab_results import write_silver_lab_results


def run_pipeline(source):
    config = PipelineConfig()
    spark = create_spark_session(config)
    try:
        bronze = write_bronze_events(spark, config, source)
        silver = write_silver_lab_results(spark, config)
        gold = write_gold_outputs(spark, config)
        return {
            "bronze": bronze,
            "silver": silver,
            "gold": gold,
        }
    finally:
        spark.stop()


def main():
    parser = argparse.ArgumentParser(description="Run the local PySpark medallion pipeline.")
    parser.add_argument("--source", choices=["jsonl", "kafka"], default="jsonl")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    summary = run_pipeline(args.source)

    print("Local PySpark medallion pipeline completed.")
    print("Bronze records written: {}".format(summary["bronze"]["records"]))
    print("Silver records written: {}".format(summary["silver"]["records"]))
    print("Gold report contexts written: {}".format(summary["gold"]["report_context"]["records"]))
    print("Dashboard KPI rows written: {}".format(summary["gold"]["dashboard_kpis"]["records"]))
    print("Bronze path: {}".format(summary["bronze"]["path"]))
    print("Silver path: {}".format(summary["silver"]["path"]))
    print("Gold report context path: {}".format(summary["gold"]["report_context"]["path"]))
    print("Gold dashboard KPIs path: {}".format(summary["gold"]["dashboard_kpis"]["path"]))


if __name__ == "__main__":
    main()
