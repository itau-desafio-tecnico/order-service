from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.app.list_orders_by_requester_use_case import ListOrdersByRequesterUseCase
from src.domain.entities import Order


@pytest.fixture
def order_repository():
    return MagicMock()


@pytest.fixture
def use_case(order_repository):
    return ListOrdersByRequesterUseCase(order_repository)


def test_execute_delegates_to_repository_and_returns_its_result(use_case, order_repository):
    requester_id = uuid4()
    order = Order.create("key-1", requester_id, "Description")
    order_repository.list_by_requester.return_value = ([order], 1)

    items, total = use_case.execute(requester_id=requester_id, page=1, size=20)

    assert items == [order]
    assert total == 1
    order_repository.list_by_requester.assert_called_once_with(requester_id=requester_id, page=1, size=20)


def test_execute_returns_empty_when_repository_finds_nothing(use_case, order_repository):
    order_repository.list_by_requester.return_value = ([], 0)

    items, total = use_case.execute(requester_id=uuid4(), page=1, size=20)

    assert items == []
    assert total == 0
