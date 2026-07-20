"""Domain entities"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

class OrderStatus(str, Enum):
    CREATED = "CREATED"

@dataclass(frozen=True)
class Order:
    id: UUID
    order_number: str
    idempotency_key: str
    requester_id: UUID
    description: str
    status: OrderStatus
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.idempotency_key or not self.idempotency_key.strip():
            raise ValueError("Idempotency key must be a non-empty string.")
        if not self.description or not self.description.strip():
            raise ValueError("Description must be a non-empty string.")
    
    @staticmethod
    def create(idempotency_key: str, requester_id: UUID, description: str) -> Order:
        now = datetime.now(timezone.utc)
        order_number = f"OS-{now:%Y%m%d}--{uuid4().hex[:6].upper()}"
        return Order(
            id=uuid4(),
            order_number=order_number,
            idempotency_key=idempotency_key,
            requester_id=requester_id,
            description=description,
            status=OrderStatus.CREATED,
            created_at=now
        )

class OutboxStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class OutboxEvent:
    id: UUID
    aggregate_type: str
    aggregate_id: UUID
    event_type: str
    payload: dict
    status: OutboxStatus
    attempts: int
    create_at: datetime
    published_at: datetime | None = None
    claimed_at: datetime | None = None

    @staticmethod
    def to_create_order(order: Order) -> "OutboxEvent":
        return OutboxEvent(
            id=uuid4(),
            aggregate_type="Order",
            aggregate_id=order.id,
            event_type="OrderCreated",
            payload={
                "order_id": str(order.id),
                "order_number": order.order_number,
                "requester_id": str(order.requester_id),
                "description": order.description,
                "status": order.status.value,
                "created_at": order.created_at.isoformat(),
            },
            status=OutboxStatus.PENDING,
            attempts=0,
            create_at=datetime.now(timezone.utc),
        )
