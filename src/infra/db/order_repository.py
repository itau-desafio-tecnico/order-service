from datetime import timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from src.domain.entities import Order, OrderStatus, OutboxEvent
from src.domain.ports import OrderRepository
from src.infra.db.models import OrderModel, OutboxEventModel


class SqlAlchemyOrderRepository(OrderRepository):
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def get_by_idempotency_key(self, idempotency_key: str, requester_id: UUID) -> Order | None:
        with self._session_factory() as session:
            model = (
                session.query(OrderModel)
                .filter_by(idempotency_key=idempotency_key, requester_id=requester_id)
                .one_or_none()
            )
            return self._to_domain(model) if model else None
    
    def save_with_outbox(self, order: Order, outbox_event: OutboxEvent) -> Order:
        with self._session_factory() as session:
            try:
                session.add(self._order_to_model(order))
                session.add(self._event_to_model(outbox_event))
                session.commit()
                return order
            except IntegrityError:
                session.rollback()
                existing_order = (
                    session.query(OrderModel)
                    .filter_by(idempotency_key=order.idempotency_key, requester_id=order.requester_id)
                    .one_or_none()
                )
                if existing_order is not None:
                    return self._to_domain(existing_order)
                else:
                    raise
        
    def list_all(self, page: int, size: int, status: OrderStatus | None = None) -> tuple[list[Order], int]:
        with self._session_factory() as session:
            query = session.query(OrderModel)
            if status is not None:
                query = query.filter(OrderModel.status == status.value)
            total = query.count()
            models = (
                query.order_by(OrderModel.created_at.desc())
                .offset((page - 1) * size)
                .limit(size)
                .all()
            )
            return [self._to_domain(model) for model in models], total

    def list_by_requester(self, requester_id: UUID, page: int, size: int) -> tuple[list[Order], int]:
        with self._session_factory() as session:
            query = session.query(OrderModel).filter(OrderModel.requester_id == requester_id)
            total = query.count()
            models = (
                query.order_by(OrderModel.created_at.desc())
                .offset((page - 1) * size)
                .limit(size)
                .all()
            )
            return [self._to_domain(model) for model in models], total

    @staticmethod
    def _order_to_model(order: Order) -> OrderModel:
        return OrderModel(
            id=order.id,
            order_number=order.order_number,
            idempotency_key=order.idempotency_key,
            requester_id=order.requester_id,
            description=order.description,
            status=order.status.value,
            created_at=order.created_at
        )
    
    @staticmethod
    def _to_domain(model: OrderModel) -> Order:
        created_at = model.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return Order(
            id=model.id,
            order_number=model.order_number,
            idempotency_key=model.idempotency_key,
            requester_id=model.requester_id,
            description=model.description,
            status=OrderStatus(model.status),
            created_at=created_at
        )

    @staticmethod
    def _event_to_model(event: OutboxEvent) -> OutboxEventModel:
        return OutboxEventModel(
            id=event.id,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            event_type=event.event_type,
            payload=event.payload,
            status=event.status.value,
            attempts=event.attempts,
            create_at=event.create_at,
        )