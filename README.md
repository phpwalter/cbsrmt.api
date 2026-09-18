# CBS Radio Mystery Theater API

Python/FastAPI implementation of the CBS Radio Mystery Theater Episode Guide API.

The checked-in `openapi.yaml` is the authoritative HTTP contract. The service exposes it at `/openapi.json` and serves Swagger UI at `/docs`.

## Architecture

HTTP client -> FastAPI -> PostgreSQL `api.*` / `admin.*` functions -> CBS RMT database.

The application does not query catalog tables directly.

## Requirements

- Python 3.12+
- PostgreSQL 16+ recommended
- `phpwalter/cbsrmt.db` branch `postgresql-v1` installed

## Windows quick start

Copy `.env.example` to `.env`, then set the PostgreSQL connection. For the current local setup:

```text
DATABASE_URL=postgresql://root@localhost:5432/cbsrmt
```

Then run:

```powershell
.\start_api.ps1
```

Default address: `http://127.0.0.1:8000`

## Main endpoints

- `GET /ping`
- `GET /episodes`
- `GET /episodes/{episodeNumber}`
- `GET /episodes/{episodeNumber}/cast`
- `GET /episodes/{episodeNumber}/writers`
- `GET /cast`
- `GET /cast/{castId}`
- `GET /cast/{castId}/episodes`
- `GET /writers`
- `GET /writers/{writerId}`
- `GET /writers/{writerId}/episodes`
- `GET /genres`
- `GET /genres/{genreId}/episodes`
- `GET /search?q=...`
- `GET /users`
- `GET/PATCH/DELETE /users/{userId}`
- `POST /oauth/token`
- `GET /docs`
- `GET /openapi.json`

## Authentication

Public catalog routes require no token. Protected user routes use Bearer JWT scopes: `read` for GET and `write` for PATCH/DELETE.

The service supports external JWKS validation or local client-credentials token issuance. Local development settings are documented in `.env.example`.

Example token request:

```powershell
curl.exe -X POST http://127.0.0.1:8000/oauth/token `
  -H "Content-Type: application/x-www-form-urlencoded" `
  -d "grant_type=client_credentials&client_id=cbsrmt-local&client_secret=change-me&scope=read write"
```

## Errors

Validation, authorization, not-found, database, and internal failures are returned as `application/problem+json` using the OpenAPI `Error` shape.

## Rate-limit headers

Responses include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`. The current OpenAPI contract does not define HTTP 429, so the middleware reports quota state without rejecting requests.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

CI runs unit tests and a PostgreSQL 16 integration test that installs the real `cbsrmt.db` schema/data and exercises the API.
