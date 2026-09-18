from __future__ import annotations

from contextlib import asynccontextmanager

import jwt
import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from psycopg import Error as PsycopgError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_settings
from .db import Database
from .middleware import RateLimitHeadersMiddleware
from .openapi_contract import load_contract
from .problems import (
    database_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from .routes import router


def create_app(database: Database | None = None) -> FastAPI:
    settings = get_settings()
    contract = load_contract()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db = database or Database(
            settings.database_url,
            settings.database_min_pool,
            settings.database_max_pool,
        )
        app.state.db = db
        app.state.settings = settings

        if settings.auth_jwks_url:
            app.state.jwks_client = jwt.PyJWKClient(settings.auth_jwks_url)
        else:
            app.state.jwks_client = None

        if database is None:
            db.open()
        try:
            yield
        finally:
            if database is None:
                db.close()

    app = FastAPI(
        title=contract["info"]["title"],
        version=contract["info"]["version"],
        description=contract["info"].get("description"),
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    app.state.settings = settings
    if database is not None:
        app.state.db = database
    if settings.auth_jwks_url:
        app.state.jwks_client = jwt.PyJWKClient(settings.auth_jwks_url)
    else:
        app.state.jwks_client = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_origin_regex=(
            r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
            if settings.app_env == "development"
            else None
        ),
        allow_credentials=False,
        allow_methods=["GET", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )
    app.add_middleware(
        RateLimitHeadersMiddleware,
        limit=settings.rate_limit_limit,
        window_seconds=settings.rate_limit_window_seconds,
    )

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(PsycopgError, database_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(router)

    @app.get("/openapi.json", include_in_schema=False)
    def contract_json() -> JSONResponse:
        return JSONResponse(contract)

    @app.get("/docs", include_in_schema=False)
    def docs() -> HTMLResponse:
        return HTMLResponse(
            """<!doctype html>
<html>
<head>
  <title>CBS RMT API Docs</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
SwaggerUIBundle({url: '/openapi.json', dom_id: '#swagger-ui'});
</script>
</body>
</html>"""
        )

    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "cbsrmt_api.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )
