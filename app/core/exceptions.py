"""Domain exceptions and the handlers that turn them into clean JSON.

Every error response has the same shape, so the frontend never has to
guess: {"error": {"code": ..., "message": ..., "detail": ...}}
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("ufms")


class UFMSError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "ufms_error"

    def __init__(self, message: str, detail: object = None):
        self.message = message
        self.detail = detail
        super().__init__(message)


class NotFoundError(UFMSError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(UFMSError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class AuthError(UFMSError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class PermissionError_(UFMSError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


def _body(code: str, message: str, detail: object = None) -> dict:
    return {"error": {"code": code, "message": message, "detail": detail}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(UFMSError)
    async def _ufms(request: Request, exc: UFMSError):
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(exc.code, exc.message, exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_body("validation_error", "Request body failed validation.",
                          exc.errors()),
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db(request: Request, exc: SQLAlchemyError):
        logger.exception("database error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_body("database_error", "A database error occurred."),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_body("internal_error", "An unexpected error occurred."),
        )
