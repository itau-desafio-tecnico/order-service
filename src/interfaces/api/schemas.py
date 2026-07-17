from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.entities import Order

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

class ErrorResponse(BaseModel):
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")