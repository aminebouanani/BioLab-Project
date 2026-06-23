"""Consume JSON messages from a local Redpanda/Kafka topic."""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from streaming.config import KafkaSettings
from streaming.consumer import KafkaConsumerTool


def main():
    parser = argparse.ArgumentParser(description="Consume BioLab Kafka topic messages.")
    parser.add_argument("--topic", required=True, help="Topic to consume, for example glims.result.")
    parser.add_argument("--max-messages", type=int, default=10, help="Maximum messages to print.")
    parser.add_argument("--timeout-seconds", type=int, default=10, help="Stop after this many empty polls.")
    parser.add_argument(
        "--bootstrap-servers",
        default=KafkaSettings().bootstrap_servers,
        help="Kafka bootstrap servers. Defaults to KAFKA_BOOTSTRAP_SERVERS or localhost:9092.",
    )
    args = parser.parse_args()

    consumer = KafkaConsumerTool(args.bootstrap_servers, args.topic)
    try:
        count = 0
        for count, message in enumerate(
            consumer.consume(args.max_messages, args.timeout_seconds),
            start=1,
        ):
            print("Message {}:".format(count))
            print(json.dumps(message, indent=2, ensure_ascii=True, sort_keys=True))
        if count == 0:
            print(
                "No messages consumed from {} within {} seconds.".format(
                    args.topic,
                    args.timeout_seconds,
                )
            )
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
