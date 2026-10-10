import asyncio
from collections.abc import Sequence


def workers_running(tasks: Sequence[asyncio.Task]) -> bool:
    """A web process is ready only while all its background workers are alive."""
    return bool(tasks) and all(not task.done() for task in tasks)
