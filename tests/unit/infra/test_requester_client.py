import httpx
import pytest
import respx

from src.domain.exceptions import RequesterServiceError
from src.infra.http.requester_client import HttpRequesterClient

BASE_URL = "http://requester-service:8081"
REQUESTER_ID = "11111111-1111-1111-1111-111111111111"


@respx.mock
def test_validate_requester_return_true_when_active():
    respx.get(f"{BASE_URL}/requesters/{REQUESTER_ID}/validation").mock(
        return_value=httpx.Response(200, json={"requesterId": REQUESTER_ID, "validation": True})
    )
    client = HttpRequesterClient(base_url=BASE_URL)

    assert client.exists(REQUESTER_ID) is True


@respx.mock
def test_validate_requester_return_false_when_inactive():
    respx.get(f"{BASE_URL}/requesters/{REQUESTER_ID}/validation").mock(
        return_value=httpx.Response(200, json={"requesterId": REQUESTER_ID, "validation": False})
    )
    client = HttpRequesterClient(base_url=BASE_URL)

    assert client.exists(REQUESTER_ID) is False


@respx.mock
def test_validate_requester_return_false_when_not_found():
    respx.get(f"{BASE_URL}/requesters/{REQUESTER_ID}/validation").mock(
        return_value=httpx.Response(404)
    )
    client = HttpRequesterClient(base_url=BASE_URL)

    assert client.exists(REQUESTER_ID) is False


@respx.mock
def test_validate_requester_throw_error_when_connection_refused():
    respx.get(f"{BASE_URL}/requesters/{REQUESTER_ID}/validation").mock(
        side_effect=httpx.ConnectError("conection refused")
    )
    client = HttpRequesterClient(base_url=BASE_URL, timeout=0.1)

    with pytest.raises(RequesterServiceError):
        client.exists(REQUESTER_ID)


@respx.mock
def test_validate_requester_throw_error_when_5xx():
    respx.get(f"{BASE_URL}/requesters/{REQUESTER_ID}/validation").mock(
        return_value=httpx.Response(500)
    )
    client = HttpRequesterClient(base_url=BASE_URL)

    with pytest.raises(RequesterServiceError):
        client.exists(REQUESTER_ID)
