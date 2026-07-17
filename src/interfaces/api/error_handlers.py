from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.domain.exceptions import RequesterNotFoundError, RequesterServiceError


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(RequesterNotFoundError)
    async def handle_requester_not_found(request: Request, exc: RequesterNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"code": "REQUEST_INVALID", "message": str(exc)},
        )

    @app.exception_handler(RequesterServiceError)
    async def handle_requester_service_error(request: Request, exc: RequesterServiceError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"code": "REQUESTER_SERVICE_ERROR", "message": str(exc)},
        )

    @app.exception_handler(ValueError)
    async def handle_value_error(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"code": "REQUEST_INVALID", "message": str(exc)},
        )
