import logging
from uuid import UUID

from src.domain.entities import Order, OutboxEvent
from src.domain.exceptions import RequesterNotFoundError
from src.domain.ports import OrderRepository, RequesterClient

logger = logging.getLogger(__name__)


class CreateOrderUseCase:

    def __init__(self, order_repository: OrderRepository, requester_client: RequesterClient):
        self._order_repository = order_repository
        self._requester_client = requester_client

    def execute(self, idempotency_key: str, requester_id: UUID, description: str) -> Order:
        existing_order = self._order_repository.get_by_idempotency_key(idempotency_key)
        if existing_order is not None:
            logger.info("Idempotent order request, returning existing order_id=%s", existing_order.id)
            return existing_order

        if not self._requester_client.exists(requester_id):
            logger.warning("Requester not found requester_id=%s", requester_id)
            raise RequesterNotFoundError(str(requester_id))

        order = Order.create(idempotency_key, requester_id, description)
        order = self._order_repository.save_with_outbox(order, OutboxEvent.to_create_order(order))
        logger.info("Order created order_id=%s order_number=%s", order.id, order.order_number)
        return order