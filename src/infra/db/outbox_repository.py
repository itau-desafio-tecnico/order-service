from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, or_

from src.domain.entities import OutboxEvent, OutboxStatus
from src.domain.ports import OutboxRepository
from src.infra.db.models import OutboxEventModel


class SqlAlchemyOutboxRepository(OutboxRepository):

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def claim_pending(self, limit: int = 20, stale_after_seconds: float = 60.0) -> list[OutboxEvent]:
        stale_threshold = datetime.now(timezone.utc) - timedelta(seconds=stale_after_seconds)
        with self._session_factory() as session:
            claimable = (
                session.query(OutboxEventModel)
                .filter(
                    or_(
                        OutboxEventModel.status == OutboxStatus.PENDING.value,
                        and_(
                            OutboxEventModel.status == OutboxStatus.PROCESSING.value,
                            OutboxEventModel.claimed_at.isnot(None),
                            OutboxEventModel.claimed_at < stale_threshold,
                        ),
                    )
                )
                .order_by(OutboxEventModel.create_at.asc())
                .limit(limit)
                .with_for_update(skip_locked=True)
                .all()
            )
            claimed_at = datetime.now(timezone.utc)
            events = []
            for model in claimable:
                model.status = OutboxStatus.PROCESSING.value
                model.claimed_at = claimed_at
                events.append(self._to_domain(model))
            session.commit()
            return events

    def mark_as_published(self, event_id: UUID) -> None:
        with self._session_factory() as session:
            session.query(OutboxEventModel).filter_by(id=event_id).update(
                {
                    "status": OutboxStatus.PUBLISHED.value,
                    "published_at": datetime.now(timezone.utc),
                }
            )
            session.commit()

    def fail_registry(self, event_id: UUID, max_attempts: int) -> None:
        with self._session_factory() as session:
            model = session.query(OutboxEventModel).filter_by(id=event_id).one_or_none()
            if model is None:
                return
            new_attempts = model.attempts + 1
            model.attempts = new_attempts
            if new_attempts >= max_attempts:
                model.status = OutboxStatus.FAILED.value
            else:
                model.status = OutboxStatus.PENDING.value
                model.claimed_at = None
            session.commit()

    @staticmethod
    def _to_domain(model: OutboxEventModel) -> OutboxEvent:
        return OutboxEvent(
            id=model.id,
            aggregate_type=model.aggregate_type,
            aggregate_id=model.aggregate_id,
            event_type=model.event_type,
            payload=model.payload,
            status=OutboxStatus(model.status),
            attempts=model.attempts,
            create_at=model.create_at,
            published_at=model.published_at,
            claimed_at=model.claimed_at,
        )
