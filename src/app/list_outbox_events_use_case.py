import logging
from datetime import datetime

from src.domain.entities import OutboxEvent, OutboxStatus
from src.domain.ports import OutboxRepository

logger = logging.getLogger(__name__)


class ListOutboxEventsUseCase:

    def __init__(self, outbox_repository: OutboxRepository):
        self._outbox_repository = outbox_repository

    def execute(
        self,
        page: int,
        size: int,
        status: OutboxStatus | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[OutboxEvent], int]:
        if created_from is not None and created_to is not None and created_from > created_to:
            raise ValueError("created_from must not be after created_to.")

        return self._outbox_repository.list_all(
            page=page,
            size=size,
            status=status,
            created_from=created_from,
            created_to=created_to,
        )
