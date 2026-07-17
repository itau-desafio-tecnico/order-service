from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities import Order, OutboxEvent

class OrderRepository(ABC):

    @abstractmethod
    def get_by_idempotency_key(self, idempotency_key: str) -> Order | None:
        ...
    
    @abstractmethod
    def save_with_outbox(self, order: Order, outbox_event: OutboxEvent) -> Order:
        ...

class OutboxRepository(ABC):

    @abstractmethod
    def search_pending(self, limit: int = 20) -> list[OutboxEvent]:
        ...

    @abstractmethod
    def mark_as_published(self, event_id: UUID) -> None:
        ...

    @abstractmethod
    def fail_registry(self, event_id: UUID, max_attempts: int) -> None:
        ...

class RequesterClient(ABC):

    @abstractmethod
    def exists(self, requester_id: UUID) -> bool:
        ...

class EventPublisher(ABC):

    @abstractmethod
    def publish(self, event: OutboxEvent) -> None:
        ...