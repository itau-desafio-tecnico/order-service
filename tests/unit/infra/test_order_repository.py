from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.domain.entities import Order, OrderStatus, OutboxEvent
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
    find = repo.get_by_idempotency_key("key-1", order.requester_id)
    assert find == order


def test_get_by_idempotency_key_returns_none_when_not_found(session_factory):
    repo = SqlAlchemyOrderRepository(session_factory)

    assert repo.get_by_idempotency_key("not_existent", uuid4()) is None


def test_save_with_outbox_handles_concurrent_requests_with_same_idempotency_key(session_factory):
    repo = SqlAlchemyOrderRepository(session_factory)
    solicitante_id = uuid4()
    order_original = Order.create("key-race", solicitante_id, "Description original")
    repo.save_with_outbox(order_original, OutboxEvent.to_create_order(order_original))

    order_duplicada = Order.create("key-race", solicitante_id, "Another description")
    resultado = repo.save_with_outbox(order_duplicada, OutboxEvent.to_create_order(order_duplicada))

    assert resultado == order_original
    assert resultado.id != order_duplicada.id


def test_save_with_outbox_allows_same_idempotency_key_for_different_requesters(session_factory):
    """Regressão: a mesma Idempotency-Key usada por dois solicitantes diferentes deve
    gerar duas ordens distintas, uma para cada solicitante — a chave de idempotência
    é escopada por (idempotency_key, requester_id), não apenas pela chave isolada.
    """
    repo = SqlAlchemyOrderRepository(session_factory)
    requester_y = uuid4()
    requester_z = uuid4()

    order_y = Order.create("key-shared", requester_y, "Description do solicitante Y")
    repo.save_with_outbox(order_y, OutboxEvent.to_create_order(order_y))

    order_z = Order.create("key-shared", requester_z, "Description do solicitante Z")
    resultado = repo.save_with_outbox(order_z, OutboxEvent.to_create_order(order_z))

    assert resultado == order_z
    assert resultado.id != order_y.id
    assert repo.get_by_idempotency_key("key-shared", requester_y) == order_y
    assert repo.get_by_idempotency_key("key-shared", requester_z) == order_z


def test_list_all_returns_paginated_orders_ordered_by_created_at_desc(session_factory):
    repo = SqlAlchemyOrderRepository(session_factory)
    requester_id = uuid4()
    for i in range(3):
        order = Order.create(f"key-{i}", requester_id, f"Description {i}")
        repo.save_with_outbox(order, OutboxEvent.to_create_order(order))

    items, total = repo.list_all(page=1, size=2)

    assert total == 3
    assert len(items) == 2


def test_list_all_second_page_returns_remaining_items(session_factory):
    repo = SqlAlchemyOrderRepository(session_factory)
    requester_id = uuid4()
    for i in range(3):
        order = Order.create(f"key-{i}", requester_id, f"Description {i}")
        repo.save_with_outbox(order, OutboxEvent.to_create_order(order))

    items, total = repo.list_all(page=2, size=2)

    assert total == 3
    assert len(items) == 1


def test_list_all_filters_by_status(session_factory):
    repo = SqlAlchemyOrderRepository(session_factory)
    order = Order.create("key-1", uuid4(), "Description")
    repo.save_with_outbox(order, OutboxEvent.to_create_order(order))

    items, total = repo.list_all(page=1, size=10, status=OrderStatus.CREATED)

    assert total == 1
    assert items[0].id == order.id


def test_list_all_returns_empty_when_no_orders(session_factory):
    repo = SqlAlchemyOrderRepository(session_factory)

    items, total = repo.list_all(page=1, size=10)

    assert items == []
    assert total == 0


def test_list_by_requester_returns_only_matching_orders(session_factory):
    repo = SqlAlchemyOrderRepository(session_factory)
    requester_a = uuid4()
    requester_b = uuid4()
    order_a = Order.create("key-a", requester_a, "Description A")
    order_b = Order.create("key-b", requester_b, "Description B")
    repo.save_with_outbox(order_a, OutboxEvent.to_create_order(order_a))
    repo.save_with_outbox(order_b, OutboxEvent.to_create_order(order_b))

    items, total = repo.list_by_requester(requester_a, page=1, size=10)

    assert total == 1
    assert items[0].id == order_a.id


def test_list_by_requester_returns_empty_when_no_match(session_factory):
    repo = SqlAlchemyOrderRepository(session_factory)

    items, total = repo.list_by_requester(uuid4(), page=1, size=10)

    assert items == []
    assert total == 0
