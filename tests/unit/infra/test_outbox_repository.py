from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.domain.entities import Order, OutboxEvent, OutboxStatus
from src.infra.db.models import Base, OutboxEventModel
from src.infra.db.order_repository import SqlAlchemyOrderRepository
from src.infra.db.outbox_repository import SqlAlchemyOutboxRepository


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _create_pending_event(session_factory) -> OutboxEvent:
    order_repo = SqlAlchemyOrderRepository(session_factory)
    order = Order.create("key-1", uuid4(), "Description")
    event = OutboxEvent.to_create_order(order)
    order_repo.save_with_outbox(order, event)
    return event


def test_claim_pending_returns_and_marks_events_as_processing(session_factory):
    event = _create_pending_event(session_factory)
    outbox_repo = SqlAlchemyOutboxRepository(session_factory)

    claimed = outbox_repo.claim_pending()

    assert len(claimed) == 1
    assert claimed[0].id == event.id
    assert claimed[0].status == OutboxStatus.PROCESSING
    assert claimed[0].claimed_at is not None


def test_claim_pending_does_not_return_already_claimed_events(session_factory):
    _create_pending_event(session_factory)
    outbox_repo = SqlAlchemyOutboxRepository(session_factory)

    first_claim = outbox_repo.claim_pending(stale_after_seconds=60.0)
    second_claim = outbox_repo.claim_pending(stale_after_seconds=60.0)

    assert len(first_claim) == 1
    assert second_claim == []


def test_claim_pending_reclaims_events_stuck_in_processing_past_the_timeout(session_factory):
    event = _create_pending_event(session_factory)
    outbox_repo = SqlAlchemyOutboxRepository(session_factory)
    outbox_repo.claim_pending(stale_after_seconds=60.0)

    with session_factory() as session:
        session.query(OutboxEventModel).filter_by(id=event.id).update(
            {"claimed_at": datetime.now(timezone.utc) - timedelta(seconds=120)}
        )
        session.commit()

    reclaimed = outbox_repo.claim_pending(stale_after_seconds=60.0)

    assert len(reclaimed) == 1
    assert reclaimed[0].id == event.id


def test_mark_as_published_removes_event_from_claimable(session_factory):
    event = _create_pending_event(session_factory)
    outbox_repo = SqlAlchemyOutboxRepository(session_factory)

    outbox_repo.mark_as_published(event.id)

    assert outbox_repo.claim_pending() == []


def test_fail_registry_increments_attempts_and_keeps_pending_until_limit(session_factory):
    event = _create_pending_event(session_factory)
    outbox_repo = SqlAlchemyOutboxRepository(session_factory)

    outbox_repo.fail_registry(event.id, max_attempts=3)

    claimed = outbox_repo.claim_pending()
    assert len(claimed) == 1
    assert claimed[0].attempts == 1
    assert claimed[0].status == OutboxStatus.PROCESSING


def test_fail_registry_marks_failed_when_limit_is_reached(session_factory):
    event = _create_pending_event(session_factory)
    outbox_repo = SqlAlchemyOutboxRepository(session_factory)

    outbox_repo.fail_registry(event.id, max_attempts=1)

    assert outbox_repo.claim_pending() == []


def test_fail_registry_ignores_nonexistent_event(session_factory):
    outbox_repo = SqlAlchemyOutboxRepository(session_factory)

    outbox_repo.fail_registry(uuid4(), max_attempts=3)
