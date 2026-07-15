from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TITLE: str = "Order Service"
    VERSION: str = "1.0.0"
    APP_NAME: str = "py-order-service"

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "order_service"
    db_user: str = "postgres"
    db_password: str = "postgres"

    requester_service_url: str = "http://localhost:8001"
    requester_timeout_seconds: float = 3.0

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

@lru_cache()
def get_settings() -> Settings:
    return Settings()
