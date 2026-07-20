import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from src.infra.config import get_settings
from src.infra.db.outbox_repository import SqlAlchemyOutboxRepository
from src.infra.db.session import SessionLocal
from src.infra.message.outbox_dispatcher import OutboxDispatcher
from src.infra.message.sns_publisher import SnsEventPublisher
from src.infra.telemetry import setup_telemetry
from src.interfaces.api.routers.orders import router as orders_router
from src.interfaces.api.error_handlers import register_exception_handlers


LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

_formatter = logging.Formatter(LOG_FORMAT)
for _uvicorn_logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    for _handler in logging.getLogger(_uvicorn_logger_name).handlers:
        _handler.setFormatter(_formatter)


class HealthCheckFilter(logging.Filter):
    """Silences uvicorn access log entries for the ALB/ECS health check probe."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

_settings = get_settings()

_dispatcher = OutboxDispatcher(
    outbox_repository=SqlAlchemyOutboxRepository(SessionLocal),
    event_publisher=SnsEventPublisher(topic_arn=_settings.sns_topic_arn, region_name=_settings.aws_region),
    poll_interval=_settings.outbox_poll_interval_seconds,
    max_attempts=_settings.outbox_max_attempts,
    processing_timeout_seconds=_settings.outbox_processing_timeout_seconds,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_dispatcher.start())
    yield
    _dispatcher.stop()
    task.cancel()


_prefix = f"/{_settings.APP_NAME}"

app = FastAPI(
    title=_settings.TITLE,
    version=_settings.VERSION,
    docs_url=f"{_prefix}/apidocs",
    openapi_url=f"{_prefix}/openapi.json",
    lifespan=lifespan
)

setup_telemetry(app)
register_exception_handlers(app)

_root_router = APIRouter(prefix=_prefix)
_root_router.include_router(orders_router)


@_root_router.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(_root_router)