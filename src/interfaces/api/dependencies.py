from fastapi import Depends

from src.app.create_order_use_case import CreateOrderUseCase
from src.app.list_orders_use_case import ListOrdersUseCase
from src.app.list_orders_by_requester_use_case import ListOrdersByRequesterUseCase
from src.app.list_outbox_events_use_case import ListOutboxEventsUseCase
from src.infra.config import get_settings
from src.infra.db.order_repository import SqlAlchemyOrderRepository
from src.infra.db.outbox_repository import SqlAlchemyOutboxRepository
from src.infra.db.session import SessionLocal
from src.infra.http.requester_client import HttpRequesterClient


def get_order_repository() -> SqlAlchemyOrderRepository:
    return SqlAlchemyOrderRepository(SessionLocal)


def get_outbox_repository() -> SqlAlchemyOutboxRepository:
    return SqlAlchemyOutboxRepository(SessionLocal)


def get_requester_client() -> HttpRequesterClient:
    settings = get_settings()
    return HttpRequesterClient(
        base_url=settings.requester_service_url,
        timeout=settings.requester_timeout_seconds,
    )


def get_create_order_use_case(
    order_repository: SqlAlchemyOrderRepository = Depends(get_order_repository),
    requester_client: HttpRequesterClient = Depends(get_requester_client),
) -> CreateOrderUseCase:
    return CreateOrderUseCase(order_repository, requester_client)


def get_list_orders_use_case(
    order_repository: SqlAlchemyOrderRepository = Depends(get_order_repository),
) -> ListOrdersUseCase:
    return ListOrdersUseCase(order_repository)


def get_list_orders_by_requester_use_case(
    order_repository: SqlAlchemyOrderRepository = Depends(get_order_repository),
) -> ListOrdersByRequesterUseCase:
    return ListOrdersByRequesterUseCase(order_repository)


def get_list_outbox_events_use_case(
    outbox_repository: SqlAlchemyOutboxRepository = Depends(get_outbox_repository),
) -> ListOutboxEventsUseCase:
    return ListOutboxEventsUseCase(outbox_repository)