from fastapi import APIRouter, Header, status, Depends

from interfaces.api.schemas import CreateOrderRequest, OrderResponse
from app.create_order_use_case import CreateOrderUseCase
from interfaces.api.dependencies import get_create_order_use_case

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    request: CreateOrderRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=255),
    use_case: CreateOrderUseCase = Depends(get_create_order_use_case)
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
    order = use_case.execute(
        idempotency_key=idempotency_key,
        requester_id=request.requester_id,
        description=request.description
    )
    return OrderResponse.from_domain(order)
