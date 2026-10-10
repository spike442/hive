from __future__ import annotations

import asyncio

from core.messaging import KafkaConsumer, KafkaMessage, KafkaTopic

from hive.domains.sre.application_service import SreApplicationService
from hive.infrastructure.config import Settings


class AlertIngress:
    """Consume Alertmanager records and start their Temporal workflows."""

    def __init__(self, settings: Settings, service: SreApplicationService, event_loop: asyncio.AbstractEventLoop):
        self.consumer = KafkaConsumer(
            settings.kafka.client(settings.kafka_username, settings.kafka_password),
            [KafkaTopic.ALERTS.value],
            f"{settings.kafka.consumer_group}-alerts",
            KafkaTopic.DEAD_LETTER.value,
            max_poll_interval_seconds=settings.kafka.max_poll_interval_seconds,
        )
        self.service = service
        self.event_loop = event_loop

    def run(self) -> None:
        self.consumer.run(self.handle)

    def handle(self, message: KafkaMessage) -> None:
        if message.topic is not KafkaTopic.ALERTS:
            raise ValueError(f"unsupported alert topic: {message.topic}")
        future = asyncio.run_coroutine_threadsafe(self.service.receive_alert_event(message.payload), self.event_loop)
        future.result()

    def stop(self) -> None:
        self.consumer.stop()

    def close(self) -> None:
        self.consumer.close()
