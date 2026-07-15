import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from infra.config import get_settings
from interfaces.api.routers.orders import router as orders_router

logging.basicConfig(level=logging.INFO)

_settings = get_settings()


app = FastAPI(
    title=_settings.TITLE,
    version=_settings.VERSION,
    doc_url=f"/{_settings.APP_NAME}/apidocs",
    openapi_url=f"/{_settings.APP_NAME}/openapi.json",
)

app.include_router(orders_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}