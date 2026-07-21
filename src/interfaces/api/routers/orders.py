import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Header, Query, status, Depends

from src.domain.entities import OrderStatus
from src.app.create_order_use_case import CreateOrderUseCase
from src.app.list_orders_use_case import ListOrdersUseCase
from src.app.list_orders_by_requester_use_case import ListOrdersByRequesterUseCase
from src.interfaces.api.schemas import CreateOrderRequest, OrderResponse, PaginatedResponse
from src.interfaces.api.dependencies import (
    get_create_order_use_case,
    get_list_orders_use_case,
    get_list_orders_by_requester_use_case,
)

logger = logging.getLogger(__name__)

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
    logger.info("Received order creation request idempotency_key=%s requester_id=%s", idempotency_key, request.requester_id)
    order = use_case.execute(
        idempotency_key=idempotency_key,
        requester_id=request.requester_id,
        description=request.description
    )
    logger.info("Order processed order_id=%s status=%s", order.id, order.status)
    return OrderResponse.from_domain(order)


@router.get("", response_model=PaginatedResponse[OrderResponse])
def get_all(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    order_status: Optional[OrderStatus] = Query(None, alias="status", description="Filter by order status"),
    use_case: ListOrdersUseCase = Depends(get_list_orders_use_case),
) -> PaginatedResponse[OrderResponse]:
    """
    List all orders, paginated and optionally filtered by status.
    """
    logger.info("Listing orders page=%s size=%s status=%s", page, size, order_status)
    orders, total = use_case.execute(page=page, size=size, status=order_status)
    return PaginatedResponse.create(
        items=[OrderResponse.from_domain(order) for order in orders],
        page=page,
        size=size,
        total=total,
    )


@router.get("/requester/{requester_id}", response_model=PaginatedResponse[OrderResponse])
def get_by_requester_id(
    requester_id: UUID,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    use_case: ListOrdersByRequesterUseCase = Depends(get_list_orders_by_requester_use_case),
) -> PaginatedResponse[OrderResponse]:
    """
    List all orders created by a given requester, paginated.
    """
    logger.info("Listing orders requester_id=%s page=%s size=%s", requester_id, page, size)
    orders, total = use_case.execute(requester_id=requester_id, page=page, size=size)
    return PaginatedResponse.create(
        items=[OrderResponse.from_domain(order) for order in orders],
        page=page,
        size=size,
        total=total,
    )
