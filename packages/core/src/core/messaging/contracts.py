from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class KafkaTopic(StrEnum):
    ALERTS = "hive.alerts"
    DEAD_LETTER = "hive.dead-letter"


@dataclass(frozen=True)
class KafkaMessage:
    topic: KafkaTopic
    payload: dict[str, Any]
