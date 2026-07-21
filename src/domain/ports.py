from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities import Order, OrderStatus, OutboxEvent, OutboxStatus

class OrderRepository(ABC):

    @abstractmethod
    def get_by_idempotency_key(self, idempotency_key: str, requester_id: UUID) -> Order | None:
        ...

    @abstractmethod
    def save_with_outbox(self, order: Order, outbox_event: OutboxEvent) -> Order:
        ...

    @abstractmethod
    def list_all(self, page: int, size: int, status: OrderStatus | None = None) -> tuple[list[Order], int]:
        ...

    @abstractmethod
    def list_by_requester(self, requester_id: UUID, page: int, size: int) -> tuple[list[Order], int]:
        ...

class OutboxRepository(ABC):

    @abstractmethod
    def claim_pending(self, limit: int = 20, stale_after_seconds: float = 60.0) -> list[OutboxEvent]:
        ...

    @abstractmethod
    def mark_as_published(self, event_id: UUID) -> None:
        ...

    @abstractmethod
    def fail_registry(self, event_id: UUID, max_attempts: int) -> None:
        ...

    @abstractmethod
    def list_all(
        self,
        page: int,
        size: int,
        status: OutboxStatus | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[OutboxEvent], int]:
        ...

class RequesterClient(ABC):

    @abstractmethod
    def exists(self, requester_id: UUID) -> bool:
        ...

class EventPublisher(ABC):

    @abstractmethod
    def publish(self, event: OutboxEvent) -> None:
        ...