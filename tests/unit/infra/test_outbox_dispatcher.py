from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.domain.entities import OutboxEvent, OutboxStatus
from src.infra.message.outbox_dispatcher import OutboxDispatcher


def _event_pending() -> OutboxEvent:
    return OutboxEvent(
        id=uuid4(),
        aggregate_type="Order",
        aggregate_id=uuid4(),
        event_type="OrderCreated",
        payload={"a": 1},
        status=OutboxStatus.PENDING,
        attempts=0,
        create_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_dispatch_once_publish_and_mark_as_published():
    outbox_repo = MagicMock()
    publisher = MagicMock()
    event = _event_pending()
    outbox_repo.claim_pending.return_value = [event]

    dispatcher = OutboxDispatcher(outbox_repo, publisher)
    await dispatcher._dispatch_once()

    publisher.publish.assert_called_once_with(event)
    outbox_repo.mark_as_published.assert_called_once_with(event.id)
    outbox_repo.fail_registry.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_once_claims_with_the_configured_processing_timeout():
    outbox_repo = MagicMock()
    publisher = MagicMock()
    outbox_repo.claim_pending.return_value = []

    dispatcher = OutboxDispatcher(outbox_repo, publisher, processing_timeout_seconds=90.0)
    await dispatcher._dispatch_once()

    outbox_repo.claim_pending.assert_called_once_with(limit=20, stale_after_seconds=90.0)


@pytest.mark.asyncio
async def test_dispatch_once_registers_failure_when_publish_raises():
    outbox_repo = MagicMock()
    publisher = MagicMock()
    event = _event_pending()
    outbox_repo.claim_pending.return_value = [event]
    publisher.publish.side_effect = RuntimeError("SNS unavailable")

    dispatcher = OutboxDispatcher(outbox_repo, publisher, max_attempts=5)
    await dispatcher._dispatch_once()

    outbox_repo.fail_registry.assert_called_once_with(event.id, max_attempts=5)
    outbox_repo.mark_as_published.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_once_does_nothing_when_no_pending_events():
    outbox_repo = MagicMock()
    publisher = MagicMock()
    outbox_repo.claim_pending.return_value = []

    dispatcher = OutboxDispatcher(outbox_repo, publisher)
    await dispatcher._dispatch_once()

    publisher.publish.assert_not_called()


def test_stop_interrupts_the_loop():
    dispatcher = OutboxDispatcher(MagicMock(), MagicMock())
    dispatcher._running = True

    dispatcher.stop()

    assert dispatcher._running is False
