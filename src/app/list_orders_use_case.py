import logging

from src.domain.entities import Order, OrderStatus
from src.domain.ports import OrderRepository

logger = logging.getLogger(__name__)


class ListOrdersUseCase:

    def __init__(self, order_repository: OrderRepository):
        self._order_repository = order_repository

    def execute(self, page: int, size: int, status: OrderStatus | None = None) -> tuple[list[Order], int]:
        return self._order_repository.list_all(page=page, size=size, status=status)
