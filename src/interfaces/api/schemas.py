from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.entities import Order, OutboxEvent

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T] = Field(..., description="Items in the current page")
    page: int = Field(..., description="Current page number (1-based)")
    size: int = Field(..., description="Number of items per page")
    total: int = Field(..., description="Total number of items matching the query")
    total_pages: int = Field(..., description="Total number of pages")

    @classmethod
    def create(cls, items: list[T], page: int, size: int, total: int) -> "PaginatedResponse[T]":
        total_pages = (total + size - 1) // size
        return cls(items=items, page=page, size=size, total=total, total_pages=total_pages)

class CreateOrderRequest(BaseModel):
    requester_id: UUID = Field(..., description="ID of the requester")
    description: str = Field(..., description="Description of the order", min_length=1, max_length=1000)

class OrderResponse(BaseModel):
    order_number: str = Field(..., description="Unique identifier for the order")
    requester_id: UUID = Field(..., description="ID of the requester")
    description: str = Field(..., description="Description of the order")
    status: str = Field(..., description="Status of the order")
    created_at: datetime = Field(..., description="Timestamp when the order was created")

    @classmethod
    def from_domain(cls, order: Order) -> "OrderResponse":
        return cls(
            order_number=order.order_number,
            requester_id=order.requester_id,
            description=order.description,
            status=order.status.value,
            created_at=order.created_at
        )

class OutboxEventResponse(BaseModel):
    id: UUID = Field(..., description="Unique identifier of the outbox event")
    aggregate_type: str = Field(..., description="Type of the aggregate that originated the event")
    aggregate_id: UUID = Field(..., description="ID of the aggregate that originated the event")
    event_type: str = Field(..., description="Type of the event")
    payload: dict = Field(..., description="Event payload")
    status: str = Field(..., description="Status of the event")
    attempts: int = Field(..., description="Number of publish attempts")
    create_at: datetime = Field(..., description="Timestamp when the event was created")
    published_at: datetime | None = Field(None, description="Timestamp when the event was published")
    claimed_at: datetime | None = Field(None, description="Timestamp when the event was last claimed")

    @classmethod
    def from_domain(cls, event: OutboxEvent) -> "OutboxEventResponse":
        return cls(
            id=event.id,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            event_type=event.event_type,
            payload=event.payload,
            status=event.status.value,
            attempts=event.attempts,
            create_at=event.create_at,
            published_at=event.published_at,
            claimed_at=event.claimed_at,
        )

class ErrorResponse(BaseModel):
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")