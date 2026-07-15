from fastapi import APIRouter, Header, status

from interfaces.api.schemas import CreateOrderRequest, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    request: CreateOrderRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=255)
) -> OrderResponse:
    """
    Create a new order.

    This endpoint allows you to create a new order by providing the necessary details in the request body.
    The `Idempotency-Key` header is required to ensure that duplicate requests are not processed multiple times.

    Args:
        request (CreateOrderRequest): The request body containing the order details.
        idempotency_key (str): A unique key provided in the `Idempotency-Key` header to ensure idempotency.

    Returns:
        OrderResponse: The response containing the created order details.
    """
    # Implementation of order creation logic goes here
    pass
