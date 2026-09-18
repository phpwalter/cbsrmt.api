from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import Error as PsycopgError
from starlette.exceptions import HTTPException as StarletteHTTPException


def problem(
    status: int,
    code: str,
    message: str,
    request: Request | None = None,
    title: str | None = None,
    type_uri: str | None = None,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "type": type_uri,
        "title": title,
        "status": status,
        "code": code,
        "message": message,
        "instance": str(request.url.path) if request else None,
    }
    return JSONResponse(
        status_code=status,
        content=payload,
        media_type="application/problem+json",
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = exc.errors()
    message = details[0].get("msg", "Invalid request") if details else "Invalid request"
    return problem(400, "bad_request", message, request, "Bad Request")


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code_map = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
    }
    return problem(
        exc.status_code,
        code_map.get(exc.status_code, "http_error"),
        str(exc.detail),
        request,
    )


async def database_exception_handler(request: Request, exc: PsycopgError) -> JSONResponse:
    # Do not expose SQL text or database internals to clients.
    return problem(
        500,
        "database_error",
        "The database operation failed.",
        request,
        "Internal Server Error",
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return problem(
        500,
        "internal_error",
        "The server encountered an unexpected error.",
        request,
        "Internal Server Error",
    )
