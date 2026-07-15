import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from domain.exceptions import RequesterServiceError
from domain.ports import RequesterClient


class HttpRequesterClient(RequesterClient):
    def __init__(self, base_url: str, timeout: float = 3.0):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(httpx.TransportError),
        reraise=True
    )
    def _get(self, path: str) -> httpx.Response:
        with httpx.Client(timeout=self._timeout) as client:
            return client.get(f"{self._base_url}{path}")
    
    def exists(self, requester_id: str) -> bool:
        try:
            response = self._get(f"/requester/{requester_id}/validation")
        except httpx.TransportError as exc:
            raise RequesterServiceError(str(exc)) from exc

        if response.status_code == 404:
            return False
        if response.status_code >= 500:
            raise RequesterServiceError(f"status={response.status_code}")

        response.raise_for_status()
        return bool(response.json().get("validation", False))