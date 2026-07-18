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
        "/py-order-service/orders",
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
        "/py-order-service/orders",
        json={"requester_id": str(uuid4()), "description": "Description"},
    )

    assert response.status_code == 422


def test_create_order_with_empty_description_returns_422():
    client = TestClient(app)

    response = client.post(
        "/py-order-service/orders",
        json={"requester_id": str(uuid4()), "description": ""},
        headers={"Idempotency-Key": "key-2"},
    )

    assert response.status_code == 422


def test_create_order_with_invalid_requester_returns_422_business_error():
    client = _client_with_use_case(FakeUseCase(exception=RequesterNotFoundError(uuid4())))

    response = client.post(
        "/py-order-service/orders",
        json={"requester_id": str(uuid4()), "description": "Description"},
        headers={"Idempotency-Key": "key-3"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_INVALID"


def test_create_order_with_unavailable_requester_returns_503():
    client = _client_with_use_case(FakeUseCase(exception=RequesterServiceError("timeout")))

    response = client.post(
        "/py-order-service/orders",
        json={"requester_id": str(uuid4()), "description": "Description"},
        headers={"Idempotency-Key": "key-4"},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "REQUESTER_SERVICE_ERROR"


def test_create_order_with_malformed_uuid_shorter_returns_422():
    client = TestClient(app)

    response = client.post(
        "/py-order-service/orders",
        json={"requester_id": "3fa85f64-5717-4562-b3fc-2c963f66afa", "description": "Description"},
        headers={"Idempotency-Key": "key-5"},
    )

    assert response.status_code == 422


def test_create_order_with_malformed_uuid_longer_returns_422():
    client = TestClient(app)

    response = client.post(
        "/py-order-service/orders",
        json={"requester_id": "3fa85f64-5717-4562-b3fc-2c963f66afaaaa", "description": "Description"},
        headers={"Idempotency-Key": "key-6"},
    )

    assert response.status_code == 422


def test_create_order_with_non_uuid_requester_id_returns_422():
    client = TestClient(app)

    response = client.post(
        "/py-order-service/orders",
        json={"requester_id": "not-a-uuid", "description": "Description"},
        headers={"Idempotency-Key": "key-7"},
    )

    assert response.status_code == 422


def test_create_order_missing_requester_id_returns_422():
    client = TestClient(app)

    response = client.post(
        "/py-order-service/orders",
        json={"description": "Description"},
        headers={"Idempotency-Key": "key-8"},
    )

    assert response.status_code == 422


def test_create_order_missing_description_returns_422():
    client = TestClient(app)

    response = client.post(
        "/py-order-service/orders",
        json={"requester_id": str(uuid4())},
        headers={"Idempotency-Key": "key-9"},
    )

    assert response.status_code == 422


def test_create_order_with_description_exceeding_max_length_returns_422():
    client = TestClient(app)

    response = client.post(
        "/py-order-service/orders",
        json={"requester_id": str(uuid4()), "description": "a" * 1001},
        headers={"Idempotency-Key": "key-10"},
    )

    assert response.status_code == 422


def test_create_order_with_description_at_max_length_boundary_returns_201():
    order = Order.create("key-11", uuid4(), "a" * 1000)
    client = _client_with_use_case(FakeUseCase(result=order))

    response = client.post(
        "/py-order-service/orders",
        json={"requester_id": str(order.requester_id), "description": "a" * 1000},
        headers={"Idempotency-Key": "key-11"},
    )

    assert response.status_code == 201


def test_create_order_with_empty_idempotency_key_returns_422():
    client = TestClient(app)

    response = client.post(
        "/py-order-service/orders",
        json={"requester_id": str(uuid4()), "description": "Description"},
        headers={"Idempotency-Key": ""},
    )

    assert response.status_code == 422


def test_create_order_with_idempotency_key_exceeding_max_length_returns_422():
    client = TestClient(app)

    response = client.post(
        "/py-order-service/orders",
        json={"requester_id": str(uuid4()), "description": "Description"},
        headers={"Idempotency-Key": "k" * 256},
    )

    assert response.status_code == 422


def test_create_order_with_idempotency_key_at_max_length_boundary_returns_201():
    key = "k" * 255
    order = Order.create(key, uuid4(), "Description")
    client = _client_with_use_case(FakeUseCase(result=order))

    response = client.post(
        "/py-order-service/orders",
        json={"requester_id": str(order.requester_id), "description": "Description"},
        headers={"Idempotency-Key": key},
    )

    assert response.status_code == 201


def test_health_endpoint():
    client = TestClient(app)

    response = client.get("/py-order-service/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
