from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

class CreateOrderRequest(BaseModel):
    requester_id: UUID = Field(..., description="ID of the requester")
    description: str = Field(..., description="Description of the order", min_length=1, max_length=1000)

class OrderResponse(BaseModel):
    order_id: str = Field(..., description="Unique identifier for the order")
    requester_id: UUID = Field(..., description="ID of the requester")
    description: str = Field(..., description="Description of the order")
    status: str = Field(..., description="Status of the order")
    created_at: datetime = Field(..., description="Timestamp when the order was created")

class ErrorResponse(BaseModel):
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")