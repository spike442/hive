import json
import logging
import threading
from collections.abc import Callable
from typing import Any

from confluent_kafka import Consumer, KafkaError, KafkaException, Producer, TopicPartition

from core.messaging.contracts import KafkaMessage, KafkaTopic

logger = logging.getLogger(__name__)


class KafkaPublisher:
    def __init__(self, config: dict[str, Any]):
        self._producer = Producer({**config, "acks": "all"})

    def publish(self, topic: str, value: dict[str, Any]) -> None:
        errors = []

        def delivered(error, _message):
            if error is not None:
                errors.append(error)

        encoded = json.dumps(value, default=str).encode()
        self._producer.produce(topic, value=encoded, on_delivery=delivered)
        remaining = self._producer.flush(30)
        if errors:
            raise KafkaException(errors[0])
        if remaining:
            raise TimeoutError(f"Kafka delivery was not confirmed for topic: {topic}")

    def close(self) -> None:
        remaining = self._producer.flush(30)
        if remaining:
            logger.error("Kafka shutdown left %s unconfirmed messages", remaining)


class KafkaConsumer:
    def __init__(
        self,
        config: dict[str, Any],
        topics: list[str],
        group_id: str,
        dead_letter_topic: str,
        max_poll_interval_seconds: int,
    ):
        consumer_config = {
            **config,
            "group.id": group_id,
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
            "max.poll.interval.ms": max_poll_interval_seconds * 1000,
        }
        self._consumer = Consumer(consumer_config)
        self._consumer.subscribe(topics)
        self._stopped = threading.Event()
        self._dead_letter_topic = dead_letter_topic
        self._dead_letter = KafkaPublisher(config)

    def run(self, handler: Callable[[KafkaMessage], None]) -> None:
        while not self._stopped.is_set():
            message = self._consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(message.error())
            raw_value = message.value().decode(errors="replace")
            try:
                payload = json.loads(raw_value)
                handler(KafkaMessage(KafkaTopic(message.topic()), payload))
            except ValueError as exc:
                logger.exception(
                    "Kafka message quarantined topic=%s partition=%s offset=%s error=%s",
                    message.topic(),
                    message.partition(),
                    message.offset(),
                    type(exc).__name__,
                )
                self._dead_letter.publish(
                    self._dead_letter_topic,
                    {
                        "source_topic": message.topic(),
                        "partition": message.partition(),
                        "offset": message.offset(),
                        "error": type(exc).__name__,
                        "value": raw_value,
                    },
                )
            except Exception:
                logger.exception(
                    "Kafka message processing failed; retrying topic=%s partition=%s offset=%s",
                    message.topic(),
                    message.partition(),
                    message.offset(),
                )
                self._consumer.seek(TopicPartition(message.topic(), message.partition(), message.offset()))
                self._stopped.wait(5)
                continue
            self._consumer.commit(message=message, asynchronous=False)

    def stop(self) -> None:
        self._stopped.set()

    def close(self) -> None:
        self._dead_letter.close()
        self._consumer.close()
