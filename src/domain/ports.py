from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities import Order

class OrderRepository(ABC):

    @abstractmethod
    def get_by_idempotency_key(self, idempotency_key: str) -> Order | None:
        ...
    
    @abstractmethod
    def save(self, order: Order) -> Order:
        ...

class RequesterClient(ABC):

    @abstractmethod
    def exists(self, requester_id: UUID) -> bool:
        ...