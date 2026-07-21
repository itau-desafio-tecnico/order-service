from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from src.domain.entities import Order, OutboxEvent, OutboxStatus
from src.interfaces.api.dependencies import get_list_outbox_events_use_case, get_outbox_repository
from src.main import app


class FakeListOutboxEventsUseCase:
    def __init__(self, items=None, total=0):
        self._items = items or []
        self._total = total
        self.last_call = None

    def execute(self, page, size, status=None, created_from=None, created_to=None):
        self.last_call = (page, size, status, created_from, created_to)
        return self._items, self._total


class FakeOutboxRepositoryStub:
    """Stub for get_outbox_repository, used to exercise the real use case through the router."""

    def list_all(self, page, size, status=None, created_from=None, created_to=None):
        return [], 0


def _client_with_use_case(fake_use_case) -> TestClient:
    app.dependency_overrides[get_list_outbox_events_use_case] = lambda: fake_use_case
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_get_all_outbox_events_returns_paginated_list():
    order = Order.create("key-1", uuid4(), "Description")
    event = OutboxEvent.to_create_order(order)
    use_case = FakeListOutboxEventsUseCase(items=[event], total=1)
    client = _client_with_use_case(use_case)

    response = client.get("/py-order-service/outbox-events", params={"page": 1, "size": 10})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["size"] == 10
    assert body["items"][0]["event_type"] == "OrderCreated"
    assert body["items"][0]["status"] == "PENDING"
    assert use_case.last_call == (1, 10, None, None, None)


def test_get_all_outbox_events_uses_default_pagination():
    use_case = FakeListOutboxEventsUseCase(items=[], total=0)
    client = _client_with_use_case(use_case)

    response = client.get("/py-order-service/outbox-events")

    assert response.status_code == 200
    assert use_case.last_call == (1, 20, None, None, None)


def test_get_all_outbox_events_filters_by_status():
    use_case = FakeListOutboxEventsUseCase(items=[], total=0)
    client = _client_with_use_case(use_case)

    response = client.get("/py-order-service/outbox-events", params={"status": "PUBLISHED"})

    assert response.status_code == 200
    assert use_case.last_call == (1, 20, OutboxStatus.PUBLISHED, None, None)


def test_get_all_outbox_events_with_invalid_status_returns_422():
    use_case = FakeListOutboxEventsUseCase()
    client = _client_with_use_case(use_case)

    response = client.get("/py-order-service/outbox-events", params={"status": "NOT_A_STATUS"})

    assert response.status_code == 422


def test_get_all_outbox_events_filters_by_created_at_range():
    use_case = FakeListOutboxEventsUseCase(items=[], total=0)
    client = _client_with_use_case(use_case)
    created_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
    created_to = datetime(2026, 1, 2, tzinfo=timezone.utc)

    response = client.get(
        "/py-order-service/outbox-events",
        params={"created_from": created_from.isoformat(), "created_to": created_to.isoformat()},
    )

    assert response.status_code == 200
    assert use_case.last_call == (1, 20, None, created_from, created_to)


def test_get_all_outbox_events_with_invalid_created_from_returns_422():
    use_case = FakeListOutboxEventsUseCase()
    client = _client_with_use_case(use_case)

    response = client.get("/py-order-service/outbox-events", params={"created_from": "not-a-date"})

    assert response.status_code == 422


def test_get_all_outbox_events_with_invalid_page_returns_422():
    use_case = FakeListOutboxEventsUseCase()
    client = _client_with_use_case(use_case)

    response = client.get("/py-order-service/outbox-events", params={"page": 0})

    assert response.status_code == 422


def test_get_all_outbox_events_with_created_from_after_created_to_returns_400():
    app.dependency_overrides[get_outbox_repository] = lambda: FakeOutboxRepositoryStub()
    client = TestClient(app)
    created_from = datetime(2026, 1, 2, tzinfo=timezone.utc)
    created_to = datetime(2026, 1, 1, tzinfo=timezone.utc)

    response = client.get(
        "/py-order-service/outbox-events",
        params={"created_from": created_from.isoformat(), "created_to": created_to.isoformat()},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "REQUEST_INVALID"
