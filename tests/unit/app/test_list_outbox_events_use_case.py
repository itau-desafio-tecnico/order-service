from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.app.list_outbox_events_use_case import ListOutboxEventsUseCase
from src.domain.entities import Order, OutboxEvent, OutboxStatus


@pytest.fixture
def outbox_repository():
    return MagicMock()


@pytest.fixture
def use_case(outbox_repository):
    return ListOutboxEventsUseCase(outbox_repository)


def test_execute_delegates_to_repository_and_returns_its_result(use_case, outbox_repository):
    order = Order.create("key-1", uuid4(), "Description")
    event = OutboxEvent.to_create_order(order)
    outbox_repository.list_all.return_value = ([event], 1)

    items, total = use_case.execute(page=1, size=20)

    assert items == [event]
    assert total == 1
    outbox_repository.list_all.assert_called_once_with(
        page=1, size=20, status=None, created_from=None, created_to=None
    )


def test_execute_forwards_status_and_date_filters_to_repository(use_case, outbox_repository):
    outbox_repository.list_all.return_value = ([], 0)
    created_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
    created_to = datetime(2026, 1, 2, tzinfo=timezone.utc)

    use_case.execute(page=1, size=20, status=OutboxStatus.PUBLISHED, created_from=created_from, created_to=created_to)

    outbox_repository.list_all.assert_called_once_with(
        page=1, size=20, status=OutboxStatus.PUBLISHED, created_from=created_from, created_to=created_to
    )


def test_execute_allows_created_from_equal_to_created_to(use_case, outbox_repository):
    outbox_repository.list_all.return_value = ([], 0)
    same_instant = datetime(2026, 1, 1, tzinfo=timezone.utc)

    use_case.execute(page=1, size=20, created_from=same_instant, created_to=same_instant)

    outbox_repository.list_all.assert_called_once()


def test_execute_raises_value_error_when_created_from_is_after_created_to(use_case, outbox_repository):
    created_from = datetime(2026, 1, 2, tzinfo=timezone.utc)
    created_to = datetime(2026, 1, 1, tzinfo=timezone.utc)

    with pytest.raises(ValueError):
        use_case.execute(page=1, size=20, created_from=created_from, created_to=created_to)

    outbox_repository.list_all.assert_not_called()


def test_execute_does_not_raise_when_only_created_from_is_in_the_future(use_case, outbox_repository):
    outbox_repository.list_all.return_value = ([], 0)
    far_future = datetime.now(timezone.utc) + timedelta(days=365)

    use_case.execute(page=1, size=20, created_from=far_future)

    outbox_repository.list_all.assert_called_once()
