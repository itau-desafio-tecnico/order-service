import logging
from uuid import UUID

from src.domain.entities import Order
from src.domain.ports import OrderRepository

logger = logging.getLogger(__name__)


class ListOrdersByRequesterUseCase:

    def __init__(self, order_repository: OrderRepository):
        self._order_repository = order_repository

    def execute(self, requester_id: UUID, page: int, size: int) -> tuple[list[Order], int]:
        return self._order_repository.list_by_requester(requester_id=requester_id, page=page, size=size)
