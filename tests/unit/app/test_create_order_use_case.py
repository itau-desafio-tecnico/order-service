from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.app.create_order_use_case import CreateOrderUseCase
from src.domain.entities import Order, OrderStatus
from src.domain.exceptions import RequesterNotFoundError


@pytest.fixture
def order_repository():
    return MagicMock()


@pytest.fixture
def requester_client():
    return MagicMock()


@pytest.fixture
def use_case(order_repository, requester_client):
    return CreateOrderUseCase(order_repository, requester_client)


def test_return_order_exists_when_idempotency_key_already_proccessed(use_case, order_repository, requester_client):
    exists = Order.create("key-123", uuid4(), "Description")
    order_repository.get_by_idempotency_key.return_value = exists

    result = use_case.execute("key-123", uuid4(), "Description")

    assert result is exists
    requester_client.exists.assert_not_called()
    order_repository.save_with_outbox.assert_not_called()


def test_create_new_order_when_requester_is_valid(use_case, order_repository, requester_client):
    order_repository.get_by_idempotency_key.return_value = None
    requester_client.exists.return_value = True
    order_repository.save_with_outbox.side_effect = lambda order, evento: order

    requester_id = uuid4()
    result = use_case.execute("key-new", requester_id, "Description")

    assert result.status == OrderStatus.CREATED
    assert result.requester_id == requester_id
    requester_client.exists.assert_called_once_with(requester_id)
    order_repository.save_with_outbox.assert_called_once()


def test_reject_order_when_requester_is_invalid(use_case, order_repository, requester_client):
    order_repository.get_by_idempotency_key.return_value = None
    requester_client.exists.return_value = False

    with pytest.raises(RequesterNotFoundError):
        use_case.execute("key-new", uuid4(), "Description")

    order_repository.save_with_outbox.assert_not_called()
