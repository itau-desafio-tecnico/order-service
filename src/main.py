import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.infra.config import get_settings
from src.infra.db.outbox_repository import SqlAlchemyOutboxRepository
from src.infra.db.session import SessionLocal
from src.infra.message.outbox_dispatcher import OutboxDispatcher
from src.infra.message.sns_publisher import SnsEventPublisher
from src.interfaces.api.routers.orders import router as orders_router
from src.interfaces.api.error_handlers import register_exception_handlers


logging.basicConfig(level=logging.INFO)

_settings = get_settings()

_dispatcher = OutboxDispatcher(
    outbox_repository=SqlAlchemyOutboxRepository(SessionLocal),
    event_publisher=SnsEventPublisher(topic_arn=_settings.sns_topic_arn, region_name=_settings.aws_region),
    poll_interval=_settings.outbox_poll_interval_seconds,
    max_attempts=_settings.outbox_max_attempts,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_dispatcher.start())
    yield
    _dispatcher.stop()
    task.cancel()


app = FastAPI(
    title=_settings.TITLE,
    version=_settings.VERSION,
    docs_url=f"/{_settings.APP_NAME}/apidocs",
    openapi_url=f"/{_settings.APP_NAME}/openapi.json",
    lifespan=lifespan
)

register_exception_handlers(app)
app.include_router(orders_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}