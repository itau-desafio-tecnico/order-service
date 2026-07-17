from datetime import datetime, timezone
from uuid import UUID

from src.domain.entities import OutboxEvent, OutboxStatus
from src.domain.ports import OutboxRepository
from src.infra.db.models import OutboxEventModel


class SqlAlchemyOutboxRepository(OutboxRepository):
    """Implementacao usada pelo OutboxDispatcher para fazer o polling
    da tabela outbox_events e atualizar o status apos a publicacao."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def search_pending(self, limit: int = 20) -> list[OutboxEvent]:
        with self._session_factory() as session:
            modelos = (
                session.query(OutboxEventModel)
                .filter(OutboxEventModel.status == OutboxStatus.PENDING.value)
                .order_by(OutboxEventModel.create_at.asc())
                .limit(limit)
                .all()
            )
            return [self._to_domain(m) for m in modelos]

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
            modelo = session.query(OutboxEventModel).filter_by(id=event_id).one_or_none()
            if modelo is None:
                return
            novas_tentativas = modelo.attempts + 1
            modelo.attempts = novas_tentativas
            modelo.status = (
                OutboxStatus.FAILED.value
                if novas_tentativas >= max_attempts
                else OutboxStatus.PENDING.value
            )
            session.commit()

    @staticmethod
    def _to_domain(modelo: OutboxEventModel) -> OutboxEvent:
        return OutboxEvent(
            id=modelo.id,
            aggregate_type=modelo.aggregate_type,
            aggregate_id=modelo.aggregate_id,
            event_type=modelo.event_type,
            payload=modelo.payload,
            status=OutboxStatus(modelo.status),
            attempts=modelo.attempts,
            create_at=modelo.create_at,
            published_at=modelo.published_at,
        )
