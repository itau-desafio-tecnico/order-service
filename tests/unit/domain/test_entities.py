from uuid import uuid4

import pytest

from src.domain.entities import Order, OrderStatus, OutboxEvent, OutboxStatus


class TestOrder:
    def test_create_generates_order_number_and_created_status(self):
        order = Order.create("key-123", uuid4(), "Preventive Maintenance")

        assert order.order_number.startswith("OS-")
        assert order.status == OrderStatus.CREATED
        assert order.idempotency_key == "key-123"
        assert order.description == "Preventive Maintenance"

    def test_rejects_empty_idempotency_key(self):
        with pytest.raises(ValueError, match="Idempotency key must be a non-empty string."):
            Order.create("   ", uuid4(), "Valid Description")

    def test_rejects_empty_description(self):
        with pytest.raises(ValueError, match="Description must be a non-empty string."):
            Order.create("key-123", uuid4(), "")

    def test_order_numbers_are_unique_between_creations(self):
        requester = uuid4()
        first = Order.create("key-1", requester, "Description")
        second = Order.create("key-2", requester, "Description")

        assert first.order_number != second.order_number
        assert first.id != second.id


class TestOutboxEvent:
    def test_to_create_order_monts_payload_correct(self):
        order = Order.create("key-123", uuid4(), "Part Replacement")

        evento = OutboxEvent.to_create_order(order)

        assert evento.event_type == "OrderCreated"
        assert evento.aggregate_type == "Order"
        assert evento.aggregate_id == order.id
        assert evento.status == OutboxStatus.PENDING
        assert evento.attempts == 0
        assert evento.payload["order_number"] == order.order_number
        assert evento.payload["requester_id"] == str(order.requester_id)
