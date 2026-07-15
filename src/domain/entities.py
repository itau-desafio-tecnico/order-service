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
