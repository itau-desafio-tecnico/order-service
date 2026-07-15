from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TITLE: str = "Order Service"
    VERSION: str = "1.0.0"
    APP_NAME: str = "py-order-service"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
