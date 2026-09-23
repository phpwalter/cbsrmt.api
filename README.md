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
- `GET /episode/today` — 50-years-ago broadcast, Central Time, cached until midnight
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


## Local episode audio library

Episode MP3 files are intentionally kept outside Git. The API can expose a local
directory as read-only media and register those URLs in
`catalog.episode_media`.

Configure `.env`:

```text
AUDIO_ROOT=C:\cbsrmt\audio
AUDIO_URL_PREFIX=/audio
AUDIO_PUBLIC_BASE_URL=http://127.0.0.1:8000/audio
```

The audio directory uses the four-digit episode-number convention:

```text
C:\cbsrmt\audio\
  0523.mp3
  0524.mp3
  0733.mp3
```

Do not add this directory to the repository.

After adding or removing local files, register the currently present MP3 files:

```powershell
.\sync_audio.ps1
```

The scanner accepts only filenames matching exactly four digits plus `.mp3`.
For example, `0523.mp3` maps to episode 523. Files that do not match an
existing episode are reported and skipped.

For each matching file, the sync command calls the existing PostgreSQL function:

```sql
admin.set_episode_audio(
    episode_number,
    stream_url,
    NULL,
    'audio/mpeg'
)
```

That function deactivates any prior active audio row for the episode and creates
the new `catalog.episode_media` row. The API then exposes the result through
`api.audio_json()`, `GET /episodes/{episodeNumber}`, and
`GET /episode/today`.

With the default development configuration, `0523.mp3` is served at:

```text
http://127.0.0.1:8000/audio/0523.mp3
```

and the database stores that URL as the episode's active audio stream URL.

The normal workflow for a new recording is therefore:

```text
copy NNNN.mp3 into AUDIO_ROOT
        |
        v
.\sync_audio.ps1
        |
        v
catalog.episode_media
        |
        v
CBS RMT API audio metadata
        |
        v
frontend Play button
```

`AUDIO_PUBLIC_BASE_URL` must be a URL that the browser running the frontend
can reach. The default loopback URL is appropriate when the frontend and browser
run on the same Windows machine.
