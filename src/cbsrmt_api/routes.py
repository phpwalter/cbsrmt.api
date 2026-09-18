from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Form, HTTPException, Path, Query, Request, Response
from pydantic import BaseModel, ConfigDict

from .auth import Principal, issue_local_token, require_read, require_write

router = APIRouter()
READ_DEPENDENCY = READ_DEPENDENCY
WRITE_DEPENDENCY = WRITE_DEPENDENCY


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
    genre: str | None = Query(None, min_length=1),
    cast: str | None = Query(None, min_length=1),
    writer: str | None = Query(None, min_length=1),
    sort: Literal["episode_number", "episode_name", "broadcast_date"] = "episode_number",
    order: Literal["asc", "desc"] = "asc",
):
    return db(request).scalar_json(
        "SELECT api.get_episodes(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (page, limit, search, year, genre, cast, writer, sort, order),
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
    limit: int = Query(5, ge=1, le=100),
    search: str | None = Query(None, min_length=1),
):
    return db(request).scalar_json("SELECT api.get_cast(%s,%s,%s)", (page, limit, search))


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
