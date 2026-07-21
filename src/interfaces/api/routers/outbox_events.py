import logging
from datetime import date, datetime, time, timezone
from typing import Annotated, Optional, Union

from fastapi import APIRouter, Query, Depends
from pydantic import BeforeValidator

from src.domain.entities import OutboxStatus
from src.app.list_outbox_events_use_case import ListOutboxEventsUseCase
from src.interfaces.api.schemas import OutboxEventResponse, PaginatedResponse
from src.interfaces.api.dependencies import get_list_outbox_events_use_case

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/outbox-events", tags=["outbox-events"])


def _parse_date_or_datetime(value: str) -> Union[date, datetime]:
    """Pydantic's lax `date` coercion accepts a full ISO datetime string whenever the time
    part is exactly midnight (e.g. "2026-01-02T00:00:00+00:00" -> date(2026, 1, 2)), which
    would make an explicit midnight timestamp indistinguishable from a bare date. Disambiguate
    from the raw string instead: only a "T"/space-less string counts as date-only."""
    if "T" in value or " " in value:
        return datetime.fromisoformat(value)
    return date.fromisoformat(value)


DateOrDatetime = Annotated[Union[date, datetime], BeforeValidator(_parse_date_or_datetime)]


def _to_datetime(value: Optional[Union[date, datetime]], end_of_day: bool) -> Optional[datetime]:
    """A bare date (no time) is ambiguous for a range boundary, so it is expanded to the
    start (00:00:00) or end (23:59:59.999999) of that day instead of defaulting to midnight,
    which would silently exclude same-day events from an inclusive `created_to` filter."""
    if value is None:
        return None
    if not isinstance(value, datetime):
        return datetime.combine(value, time.max if end_of_day else time.min, tzinfo=timezone.utc)
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


@router.get("", response_model=PaginatedResponse[OutboxEventResponse])
def get_all(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    event_status: Optional[OutboxStatus] = Query(None, alias="status", description="Filter by event status"),
    created_from: Optional[DateOrDatetime] = Query(
        None, description="Filter events created at or after this timestamp. A bare date (YYYY-MM-DD) is treated as the start of that day."
    ),
    created_to: Optional[DateOrDatetime] = Query(
        None, description="Filter events created at or before this timestamp. A bare date (YYYY-MM-DD) is treated as the end of that day."
    ),
    use_case: ListOutboxEventsUseCase = Depends(get_list_outbox_events_use_case),
) -> PaginatedResponse[OutboxEventResponse]:
    """
    List all outbox events, paginated and optionally filtered by status and creation date.
    """
    normalized_created_from = _to_datetime(created_from, end_of_day=False)
    normalized_created_to = _to_datetime(created_to, end_of_day=True)
    logger.info(
        "Listing outbox events page=%s size=%s status=%s created_from=%s created_to=%s",
        page, size, event_status, normalized_created_from, normalized_created_to,
    )
    events, total = use_case.execute(
        page=page,
        size=size,
        status=event_status,
        created_from=normalized_created_from,
        created_to=normalized_created_to,
    )
    return PaginatedResponse.create(
        items=[OutboxEventResponse.from_domain(event) for event in events],
        page=page,
        size=size,
        total=total,
    )
