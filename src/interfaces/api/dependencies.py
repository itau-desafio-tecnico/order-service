from fastapi import Depends

from src.app.create_order_use_case import CreateOrderUseCase
from src.infra.config import get_settings
from src.infra.db.order_repository import SqlAlchemyOrderRepository
from src.infra.db.session import SessionLocal
from src.infra.http.requester_client import HttpRequesterClient


def get_order_repository() -> SqlAlchemyOrderRepository:
    return SqlAlchemyOrderRepository(SessionLocal)


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