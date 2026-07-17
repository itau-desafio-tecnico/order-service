from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.domain.entities import Order, OutboxEvent
from src.infra.db.models import Base
from src.infra.db.order_repository import SqlAlchemyOrderRepository


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_save_with_outbox_persists_order_and_allows_lookup_by_idempotency_key(session_factory):
    repo = SqlAlchemyOrderRepository(session_factory)
    order = Order.create("key-1", uuid4(), "Description")
    event = OutboxEvent.to_create_order(order)

    save = repo.save_with_outbox(order, event)

    assert save == order
    find = repo.get_by_idempotency_key("key-1")
    assert find == order


def test_get_by_idempotency_key_returns_none_when_not_found(session_factory):
    repo = SqlAlchemyOrderRepository(session_factory)

    assert repo.get_by_idempotency_key("not_existent") is None


def test_save_with_outbox_handles_concurrent_requests_with_same_idempotency_key(session_factory):
    repo = SqlAlchemyOrderRepository(session_factory)
    solicitante_id = uuid4()
    order_original = Order.create("key-race", solicitante_id, "Description original")
    repo.save_with_outbox(order_original, OutboxEvent.to_create_order(order_original))

    order_duplicada = Order.create("key-race", solicitante_id, "Another description")
    resultado = repo.save_with_outbox(order_duplicada, OutboxEvent.to_create_order(order_duplicada))

    assert resultado == order_original
    assert resultado.id != order_duplicada.id
