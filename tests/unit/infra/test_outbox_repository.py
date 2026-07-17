from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.domain.entities import Order, OutboxEvent, OutboxStatus
from src.infra.db.models import Base
from src.infra.db.order_repository import SqlAlchemyOrderRepository
from src.infra.db.outbox_repository import SqlAlchemyOutboxRepository


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _criar_event_pending(session_factory):
    order_repo = SqlAlchemyOrderRepository(session_factory)
    order = Order.create("key-1", uuid4(), "Description")
    event = OutboxEvent.to_create_order(order)
    order_repo.save_with_outbox(order, event)
    return event


def test_search_pending_returns_events_pending(session_factory):
    event = _criar_event_pending(session_factory)
    outbox_repo = SqlAlchemyOutboxRepository(session_factory)

    pendentes = outbox_repo.search_pending()

    assert len(pendentes) == 1
    assert pendentes[0].id == event.id
    assert pendentes[0].status == OutboxStatus.PENDING


def test_marcar_publicado_remove_da_lista_de_pendentes(session_factory):
    event = _criar_event_pending(session_factory)
    outbox_repo = SqlAlchemyOutboxRepository(session_factory)

    outbox_repo.mark_as_published(event.id)

    assert outbox_repo.search_pending() == []


def test_registrar_falha_incrementa_tentativas_e_mantem_pending_ate_limite(session_factory):
    event = _criar_event_pending(session_factory)
    outbox_repo = SqlAlchemyOutboxRepository(session_factory)

    outbox_repo.fail_registry(event.id, max_attempts=3)

    pendentes = outbox_repo.search_pending()
    assert len(pendentes) == 1
    assert pendentes[0].attempts == 1
    assert pendentes[0].status == OutboxStatus.PENDING


def test_registrar_falha_marca_failed_ao_atingir_limite(session_factory):
    event = _criar_event_pending(session_factory)
    outbox_repo = SqlAlchemyOutboxRepository(session_factory)

    outbox_repo.fail_registry(event.id, max_attempts=1)

    assert outbox_repo.search_pending() == []


def test_registrar_falha_ignora_event_inexistente(session_factory):
    outbox_repo = SqlAlchemyOutboxRepository(session_factory)

    outbox_repo.fail_registry(uuid4(), max_attempts=3)
