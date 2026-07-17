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
    outbox_repo.search_pending.return_value = [event]

    dispatcher = OutboxDispatcher(outbox_repo, publisher)
    await dispatcher._dispatch_once()

    publisher.publish.assert_called_once_with(event)
    outbox_repo.mark_as_published.assert_called_once_with(event.id)
    outbox_repo.fail_registry.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_once_registra_falha_quando_publish_lanca_erro():
    outbox_repo = MagicMock()
    publisher = MagicMock()
    event = _event_pending()
    outbox_repo.search_pending.return_value = [event]
    publisher.publish.side_effect = RuntimeError("SNS indisponível")

    dispatcher = OutboxDispatcher(outbox_repo, publisher, max_attempts=5)
    await dispatcher._dispatch_once()

    outbox_repo.fail_registry.assert_called_once_with(event.id, max_attempts=5)
    outbox_repo.mark_as_published.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_once_nao_faz_nada_quando_sem_pendentes():
    outbox_repo = MagicMock()
    publisher = MagicMock()
    outbox_repo.search_pending.return_value = []

    dispatcher = OutboxDispatcher(outbox_repo, publisher)
    await dispatcher._dispatch_once()

    publisher.publish.assert_not_called()


def test_stop_interrompe_o_loop():
    dispatcher = OutboxDispatcher(MagicMock(), MagicMock())
    dispatcher._running = True

    dispatcher.stop()

    assert dispatcher._running is False
