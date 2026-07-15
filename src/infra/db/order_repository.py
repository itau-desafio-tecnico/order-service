from sqlalchemy.exc import IntegrityError

from domain.entities import Order, OrderStatus
from domain.ports import OrderRepository
from infra.db.models import OrderModel


class SqlAlchemyOrderRepository(OrderRepository):
    def __init__(self, session_factory):
        self._session_factory = session_factory
    
    def get_by_idempotency_key(self, idempotency_key: str) -> Order | None:
        with self._session_factory() as session:
            model = (
                session.query(OrderModel)
                .filter_by(idempotency_key=idempotency_key)
                .one_or_none()
            )
            return self._to_domain(model) if model else None
    
    def save(self, order: Order) -> Order:
        with self._session_factory() as session:
            try:
                session.add(self._order_to_model(order))
                session.commit()
                return order
            except IntegrityError:
                session.rollback()
                existing_order = (
                    session.query(OrderModel)
                    .filter_by(idempotency_key=order.idempotency_key)
                    .one_or_none()
                )
                if existing_order is not None:
                    return self._to_domain(existing_order)
                else:
                    raise
        
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
        return Order(
            id=model.id,
            order_number=model.order_number,
            idempotency_key=model.idempotency_key,
            requester_id=model.requester_id,
            description=model.description,
            status=OrderStatus(model.status),
            created_at=model.created_at
        )