from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from threading import Lock
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, HTTPException, Path, Query, Request, Response
from pydantic import BaseModel, ConfigDict

from .auth import Principal, issue_local_token, require_read, require_write

router = APIRouter()
READ_DEPENDENCY = Depends(require_read)
WRITE_DEPENDENCY = Depends(require_write)


CENTRAL = ZoneInfo("America/Chicago")
_today_cache_lock = Lock()
_today_cache: dict[str, Any] = {}


def _today_cache_key(now: datetime) -> str:
    return now.date().isoformat()


def _end_of_day(now: datetime) -> datetime:
    tomorrow = now.date() + timedelta(days=1)
    return datetime.combine(tomorrow, time.min, tzinfo=CENTRAL) - timedelta(microseconds=1)


def _years_ago_date(now: datetime, years: int) -> date:
    try:
        return now.date().replace(year=now.year - years)
    except ValueError:
        # February 29 maps to February 28 when the target year is not a leap year.
        return now.date().replace(year=now.year - years, day=28)


@router.get("/episode/today", operation_id="getEpisodeToday")
def get_episode_today(request: Request, response: Response):
    now = datetime.now(CENTRAL)
    key = _today_cache_key(now)

    with _today_cache_lock:
        cached = _today_cache.get(key)
        if cached is not None and cached["expires_at"] > now:
            ttl = max(int((cached["expires_at"] - now).total_seconds()), 0)
            response.headers["Cache-Control"] = f"public, max-age={ttl}"
            response.headers["Expires"] = cached["expires_at"].astimezone(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
            return cached["payload"]

    target_date = _years_ago_date(now, 50)
    resolved = db(request).scalar_json(
        "SELECT api.get_anniversary_broadcasts(%s)",
        (target_date,),
    )

    expires_at = _end_of_day(now)
    payload = {
        "today": now.date().isoformat(),
        "anniversary_date": target_date.isoformat(),
        "years_ago": 50,
        "resolved_broadcast_date": resolved.get("resolved_broadcast_date") if resolved else None,
        "fallback_used": bool(resolved and resolved.get("fallback_used")),
        "broadcasts": resolved.get("broadcasts", []) if resolved else [],
        "cache_expires_at": expires_at.isoformat(),
    }

    with _today_cache_lock:
        _today_cache.clear()
        _today_cache[key] = {"expires_at": expires_at, "payload": payload}

    ttl = max(int((expires_at - now).total_seconds()), 0)
    response.headers["Cache-Control"] = f"public, max-age={ttl}"
    response.headers["Expires"] = expires_at.astimezone(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
    return payload


@router.post("/oauth/token", include_in_schema=False)
def oauth_token(
    request: Request,
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    scope: str = Form("read"),
):
    if grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail="Only client_credentials is supported.")
    return issue_local_token(client_id, client_secret, scope, request)



def db(request: Request):
    return request.app.state.db


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    avatar: dict[str, str] | None = None


def found(value: Any, resource: str) -> Any:
    if value is None:
        raise HTTPException(status_code=404, detail=f"{resource} was not found.")
    return value


@router.get("/ping", operation_id="ping")
def ping(request: Request):
    return db(request).scalar_json("SELECT api.ping()")


@router.get("/episodes", operation_id="listEpisodes")
def list_episodes(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(5, ge=1, le=100),
    search: str | None = Query(None, min_length=1),
    year: int | None = Query(None, ge=1974, le=1982),
    genre: Annotated[list[str] | None, Query()] = None,
    cast: str | None = Query(None, min_length=1),
    writer: str | None = Query(None, min_length=1),
    sort: Literal["episode_number", "episode_name", "broadcast_date"] = "episode_number",
    order: Literal["asc", "desc"] = "asc",
    episode: int | None = Query(None, ge=1),
):
    return db(request).scalar_json(
        "SELECT api.get_episodes(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (page, limit, search, year, ",".join(genre) if genre else None, cast, writer, sort, order, episode),
    )


@router.get("/episodes/{episodeNumber}", operation_id="getEpisodeByNumber")
def get_episode(request: Request, episodeNumber: int = Path(..., ge=1)):
    value = db(request).scalar_json("SELECT api.get_episode(%s)", (episodeNumber,))
    return found(value, "Episode")


@router.get("/episodes/{episodeNumber}/cast", operation_id="getEpisodeCast")
def get_episode_cast(request: Request, episodeNumber: int = Path(..., ge=1)):
    value = db(request).scalar_json("SELECT api.get_episode_cast(%s)", (episodeNumber,))
    return found(value, "Episode")


@router.get("/episodes/{episodeNumber}/writers", operation_id="getEpisodeWriters")
def get_episode_writers(request: Request, episodeNumber: int = Path(..., ge=1)):
    value = db(request).scalar_json("SELECT api.get_episode_writers(%s)", (episodeNumber,))
    return found(value, "Episode")


@router.get("/cast", operation_id="listCast")
def list_cast(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = Query(None, min_length=1),
    initial: str | None = Query(None, min_length=1, max_length=1),
    sort: Literal["appearances", "name"] = "appearances",
    order: Literal["asc", "desc"] = "desc",
):
    return db(request).scalar_json(
        "SELECT api.get_cast(%s,%s,%s,%s,%s,%s)",
        (page, limit, search, initial, sort, order),
    )


@router.get("/cast/{castId}", operation_id="getCastMember")
def get_cast_member(request: Request, castId: int = Path(..., ge=1)):
    value = db(request).scalar_json("SELECT api.get_cast_member(%s)", (castId,))
    return found(value, "Cast member")


@router.get("/cast/{castId}/episodes", operation_id="listEpisodesByCastMember")
def list_cast_episodes(
    request: Request,
    castId: int = Path(..., ge=1),
    page: int = Query(1, ge=1),
    limit: int = Query(5, ge=1, le=100),
    sort: Literal["episode_number", "episode_name", "broadcast_date"] = "episode_number",
    order: Literal["asc", "desc"] = "asc",
):
    value = db(request).scalar_json(
        "SELECT api.get_cast_episodes(%s,%s,%s,%s,%s)",
        (castId, page, limit, sort, order),
    )
    return found(value, "Cast member")


@router.get("/writers", operation_id="listWriters")
def list_writers(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(5, ge=1, le=100),
    search: str | None = Query(None, min_length=1),
):
    return db(request).scalar_json("SELECT api.get_writers(%s,%s,%s)", (page, limit, search))


@router.get("/writers/{writerId}", operation_id="getWriter")
def get_writer(request: Request, writerId: int = Path(..., ge=1)):
    value = db(request).scalar_json("SELECT api.get_writer(%s)", (writerId,))
    return found(value, "Writer")


@router.get("/writers/{writerId}/episodes", operation_id="listEpisodesByWriter")
def list_writer_episodes(
    request: Request,
    writerId: int = Path(..., ge=1),
    page: int = Query(1, ge=1),
    limit: int = Query(5, ge=1, le=100),
    sort: Literal["episode_number", "episode_name", "broadcast_date"] = "episode_number",
    order: Literal["asc", "desc"] = "asc",
):
    value = db(request).scalar_json(
        "SELECT api.get_writer_episodes(%s,%s,%s,%s,%s)",
        (writerId, page, limit, sort, order),
    )
    return found(value, "Writer")


@router.get("/genres", operation_id="listGenres")
def list_genres(request: Request):
    return db(request).scalar_json("SELECT api.get_genres()")


@router.get("/genres/{genreId}/episodes", operation_id="listEpisodesByGenre")
def list_genre_episodes(
    request: Request,
    genreId: int = Path(..., ge=1),
    page: int = Query(1, ge=1),
    limit: int = Query(5, ge=1, le=100),
    sort: Literal["episode_number", "episode_name", "broadcast_date"] = "episode_number",
    order: Literal["asc", "desc"] = "asc",
):
    value = db(request).scalar_json(
        "SELECT api.get_genre_episodes(%s,%s,%s,%s,%s)",
        (genreId, page, limit, sort, order),
    )
    return found(value, "Genre")


@router.get("/search", operation_id="searchCatalog")
def search_catalog(
    request: Request,
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(5, ge=1, le=100),
):
    return db(request).scalar_json("SELECT api.search_catalog(%s,%s,%s)", (q, page, limit))


@router.get("/users", operation_id="listUsers")
def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(5, ge=1, le=100),
    _: Principal = READ_DEPENDENCY,
):
    return db(request).scalar_json("SELECT api.get_users(%s,%s)", (page, limit))


@router.get("/users/{userId}", operation_id="getUserById")
def get_user(
    request: Request,
    userId: int = Path(..., ge=1),
    _: Principal = READ_DEPENDENCY,
):
    value = db(request).scalar_json("SELECT api.get_user(%s)", (userId,))
    return found(value, "User")


@router.patch("/users/{userId}", operation_id="updateUser")
def update_user(
    request: Request,
    userId: int = Path(..., ge=1),
    patch: UserUpdate | None = None,
    _: Principal = WRITE_DEPENDENCY,
):
    payload = {} if patch is None else patch.model_dump(exclude_unset=True)
    value = db(request).scalar_json("SELECT admin.update_user(%s,%s::jsonb)", (userId, payload))
    return found(value, "User")


@router.delete("/users/{userId}", operation_id="deleteUser", status_code=204)
def delete_user(
    request: Request,
    userId: int = Path(..., ge=1),
    _: Principal = WRITE_DEPENDENCY,
):
    deleted = db(request).execute_scalar("SELECT admin.delete_user(%s)", (userId,))
    if not deleted:
        raise HTTPException(status_code=404, detail="User was not found.")
    return Response(status_code=204)
