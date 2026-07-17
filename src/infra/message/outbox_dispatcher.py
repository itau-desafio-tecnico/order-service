import asyncio
import logging

from src.domain.ports import EventPublisher, OutboxRepository

logger = logging.getLogger(__name__)


class OutboxDispatcher:

    def __init__(
        self,
        outbox_repository: OutboxRepository,
        event_publisher: EventPublisher,
        poll_interval: float = 2.0,
        max_attempts: int = 5,
    ) -> None:
        self._outbox_repository = outbox_repository
        self._event_publisher = event_publisher
        self._poll_interval = poll_interval
        self._max_attempts = max_attempts
        self._running = False

    async def start(self) -> None:
        self._running = True
        while self._running:
            await self._dispatch_once()
            await asyncio.sleep(self._poll_interval)

    def stop(self) -> None:
        self._running = False

    async def _dispatch_once(self) -> None:
        pending_events = self._outbox_repository.search_pending(limit=20)
        for event in pending_events:
            try:
                self._event_publisher.publish(event)
                self._outbox_repository.mark_as_published(event.id)
            except Exception:
                logger.exception("Fail to publish outbox event id=%s", event.id)
                self._outbox_repository.fail_registry(event.id, max_attempts=self._max_attempts)
