import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Depends

from src.domain.entities import OutboxStatus
from src.app.list_outbox_events_use_case import ListOutboxEventsUseCase
from src.interfaces.api.schemas import OutboxEventResponse, PaginatedResponse
from src.interfaces.api.dependencies import get_list_outbox_events_use_case

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/outbox-events", tags=["outbox-events"])


@router.get("", response_model=PaginatedResponse[OutboxEventResponse])
def get_all(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    event_status: Optional[OutboxStatus] = Query(None, alias="status", description="Filter by event status"),
    created_from: Optional[datetime] = Query(None, description="Filter events created at or after this timestamp"),
    created_to: Optional[datetime] = Query(None, description="Filter events created at or before this timestamp"),
    use_case: ListOutboxEventsUseCase = Depends(get_list_outbox_events_use_case),
) -> PaginatedResponse[OutboxEventResponse]:
    """
    List all outbox events, paginated and optionally filtered by status and creation date.
    """
    logger.info(
        "Listing outbox events page=%s size=%s status=%s created_from=%s created_to=%s",
        page, size, event_status, created_from, created_to,
    )
    events, total = use_case.execute(
        page=page,
        size=size,
        status=event_status,
        created_from=created_from,
        created_to=created_to,
    )
    return PaginatedResponse.create(
        items=[OutboxEventResponse.from_domain(event) for event in events],
        page=page,
        size=size,
        total=total,
    )
