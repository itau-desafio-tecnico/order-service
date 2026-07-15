from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy import Uuid as ASUuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(ASUuid(as_uuid=True), primary_key=True)
    order_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    requester_id: Mapped[UUID] = mapped_column(ASUuid(as_uuid=True), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)