from uuid import uuid4

from fastapi.testclient import TestClient

from src.domain.entities import Order
from src.domain.exceptions import RequesterServiceError, RequesterNotFoundError
from src.interfaces.api.dependencies import get_create_order_use_case
from src.main import app


class FakeUseCase:
    def __init__(self, result=None, exception=None):
        self._result = result
        self._exception = exception

    def execute(self, idempotency_key, requester_id, description):
        if self._exception:
            raise self._exception
        return self._result


def _client_with_use_case(fake_use_case) -> TestClient:
    app.dependency_overrides[get_create_order_use_case] = lambda: fake_use_case
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_create_order_return_201():
    order = Order.create("key-1", uuid4(), "Description")
    client = _client_with_use_case(FakeUseCase(result=order))

    response = client.post(
        "/orders",
        json={"requester_id": str(order.requester_id), "description": "Description"},
        headers={"Idempotency-Key": "key-1"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["order_number"] == order.order_number
    assert body["status"] == "CREATED"


def test_create_order_without_idempotency_key_returns_422():
    client = TestClient(app)

    response = client.post(
        "/orders",
        json={"requester_id": str(uuid4()), "description": "Description"},
    )

    assert response.status_code == 422


def test_create_order_with_empty_description_returns_422():
    client = TestClient(app)

    response = client.post(
        "/orders",
        json={"requester_id": str(uuid4()), "description": ""},
        headers={"Idempotency-Key": "key-2"},
    )

    assert response.status_code == 422


def test_create_order_with_invalid_requester_returns_422_business_error():
    client = _client_with_use_case(FakeUseCase(exception=RequesterNotFoundError(uuid4())))

    response = client.post(
        "/orders",
        json={"requester_id": str(uuid4()), "description": "Description"},
        headers={"Idempotency-Key": "key-3"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_INVALID"


def test_create_order_with_unavailable_requester_returns_503():
    client = _client_with_use_case(FakeUseCase(exception=RequesterServiceError("timeout")))

    response = client.post(
        "/orders",
        json={"requester_id": str(uuid4()), "description": "Description"},
        headers={"Idempotency-Key": "key-4"},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "REQUESTER_SERVICE_ERROR"


def test_health_endpoint():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
