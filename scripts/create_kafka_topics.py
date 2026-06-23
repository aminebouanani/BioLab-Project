"""Create local Redpanda/Kafka topics used by BioLab."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from streaming.config import KafkaSettings
from streaming.topics import ALL_TOPICS


def create_topics(bootstrap_servers, topics):
    try:
        from confluent_kafka.admin import AdminClient, NewTopic
    except ImportError as exc:
        raise RuntimeError(
            "confluent-kafka is required. Install dependencies with "
            "'pip install -r requirements.txt'."
        ) from exc

    admin = AdminClient({"bootstrap.servers": bootstrap_servers})
    metadata = admin.list_topics(timeout=10)
    existing_topics = set(metadata.topics.keys())
    missing_topics = [topic for topic in topics if topic not in existing_topics]

    if not missing_topics:
        print("All Kafka topics already exist: {}".format(", ".join(topics)))
        return

    futures = admin.create_topics(
        [NewTopic(topic, num_partitions=1, replication_factor=1) for topic in missing_topics]
    )
    for topic, future in futures.items():
        try:
            future.result()
            print("Created topic: {}".format(topic))
        except Exception as exc:
            print("Topic {} could not be created: {}".format(topic, exc), file=sys.stderr)
            raise


def main():
    parser = argparse.ArgumentParser(description="Create BioLab Kafka topics in Redpanda.")
    parser.add_argument(
        "--bootstrap-servers",
        default=KafkaSettings().bootstrap_servers,
        help="Kafka bootstrap servers. Defaults to KAFKA_BOOTSTRAP_SERVERS or localhost:9092.",
    )
    args = parser.parse_args()

    create_topics(args.bootstrap_servers, ALL_TOPICS)


if __name__ == "__main__":
    main()
