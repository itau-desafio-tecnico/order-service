from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.app.list_orders_use_case import ListOrdersUseCase
from src.domain.entities import Order, OrderStatus


@pytest.fixture
def order_repository():
    return MagicMock()


@pytest.fixture
def use_case(order_repository):
    return ListOrdersUseCase(order_repository)


def test_execute_delegates_to_repository_and_returns_its_result(use_case, order_repository):
    order = Order.create("key-1", uuid4(), "Description")
    order_repository.list_all.return_value = ([order], 1)

    items, total = use_case.execute(page=1, size=20, status=None)

    assert items == [order]
    assert total == 1
    order_repository.list_all.assert_called_once_with(page=1, size=20, status=None)


def test_execute_forwards_status_filter_to_repository(use_case, order_repository):
    order_repository.list_all.return_value = ([], 0)

    use_case.execute(page=1, size=20, status=OrderStatus.CREATED)

    order_repository.list_all.assert_called_once_with(page=1, size=20, status=OrderStatus.CREATED)
