from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Callable, Optional

from common import config

if TYPE_CHECKING:
    from confluent_kafka import Consumer, Producer

logger = logging.getLogger(__name__)


def create_producer(max_retries: int = 30, retry_delay_seconds: float = 2.0) -> "Producer":
    from confluent_kafka import KafkaException, Producer

    last_err: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            producer = Producer({"bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS})
            producer.list_topics(timeout=5)
            logger.info("Połączono z Kafką (%s) po %d próbie(ach).", config.KAFKA_BOOTSTRAP_SERVERS, attempt)
            return producer
        except KafkaException as exc:
            last_err = exc
            logger.warning(
                "Kafka niedostępna (próba %d/%d): %s. Ponawiam za %.1fs...",
                attempt, max_retries, exc, retry_delay_seconds,
            )
            time.sleep(retry_delay_seconds)
    raise RuntimeError(f"Nie udało się połączyć z Kafką po {max_retries} próbach") from last_err


def create_consumer(group_id: str, topics: list[str], max_retries: int = 30,
                     retry_delay_seconds: float = 2.0) -> "Consumer":
    from confluent_kafka import Consumer, KafkaException

    last_err: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            consumer = Consumer({
                "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
                "group.id": group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": True,
            })
            consumer.list_topics(timeout=5)
            consumer.subscribe(topics)
            logger.info(
                "Konsument '%s' połączony z Kafką, subskrybuje %s (próba %d).",
                group_id, topics, attempt,
            )
            return consumer
        except KafkaException as exc:
            last_err = exc
            logger.warning(
                "Kafka niedostępna (próba %d/%d): %s. Ponawiam za %.1fs...",
                attempt, max_retries, exc, retry_delay_seconds,
            )
            time.sleep(retry_delay_seconds)
    raise RuntimeError(f"Nie udało się połączyć z Kafką po {max_retries} próbach") from last_err


def produce_json(producer: "Producer", topic: str, key: str, payload: dict,
                  on_delivery: Optional[Callable] = None) -> None:
    producer.produce(
        topic=topic,
        key=key.encode("utf-8"),
        value=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        callback=on_delivery,
    )
    producer.poll(0)
