from uuid import UUID

from domain.entities import Order, OutboxEvent
from domain.exceptions import RequesterNotFoundError
from domain.ports import OrderRepository, RequesterClient


class CreateOrderUseCase:

    def __init__(self, order_repository: OrderRepository, requester_client: RequesterClient):
        self._order_repository = order_repository
        self._requester_client = requester_client
    
    def execute(self, idempotency_key: str, requester_id: UUID, description: str) -> Order:
        existing_order = self._order_repository.get_by_idempotency_key(idempotency_key)
        if existing_order is not None:
            return existing_order
        
        if not self._requester_client.exists(requester_id):
            raise RequesterNotFoundError(str(requester_id))
        
        order = Order.create(idempotency_key, requester_id, description)
        return self._order_repository.save_with_outbox(order, OutboxEvent.to_create_order(order))