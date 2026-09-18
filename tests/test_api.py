from __future__ import annotations

from contextlib import contextmanager

from fastapi.testclient import TestClient

from cbsrmt_api.main import create_app


class FakeDatabase:
    def __init__(self):
        self.calls = []

    def scalar_json(self, sql, params=()):
        self.calls.append((sql, params))
        if "api.ping" in sql:
            return {"status": "ok"}
        if "api.get_episode(" in sql:
            if params[0] == 999999:
                return None
            return {
                "episode_number": params[0],
                "episode_name": "Test Episode",
                "episode_plot": None,
                "broadcast_date": "1974-01-06",
                "thumbnail": f"/public/assets/episodes/{params[0]}.png",
                "audio": {
                    "available": False,
                    "stream_url": None,
                    "duration_seconds": None,
                    "media_type": None,
                },
                "genres": [],
                "cast": [],
                "writers": [],
            }
        if "api.get_episodes" in sql:
            page, limit = params[0], params[1]
            return {
                "data": [],
                "pagination": {"page": page, "limit": limit, "total": 0, "pages": 0},
            }
        if "api.get_genres" in sql:
            return {"data": [{"id": 1, "name": "Mystery"}]}
        if "api.search_catalog" in sql:
            return {
                "data": {"episodes": [], "cast": [], "writers": []},
                "pagination": {"page": params[1], "limit": params[2], "total": 0, "pages": 0},
            }
        if "api.get_users" in sql:
            return {"data": [], "pagination": {"page": 1, "limit": 5, "total": 0, "pages": 0}}
        if "api.get_user" in sql:
            return None if params[0] == 999999 else {
                "id": params[0],
                "username": "test",
                "first_name": "Test",
                "last_name": "User",
            }
        if "admin.update_user" in sql:
            return {
                "id": params[0],
                "username": "test",
                "first_name": params[1].get("first_name", "Test"),
                "last_name": "User",
            }
        return {"data": []}

    def execute_scalar(self, sql, params=()):
        self.calls.append((sql, params))
        if "admin.delete_user" in sql:
            return params[0] != 999999
        return None


@contextmanager
def client():
    db = FakeDatabase()
    app = create_app(database=db)
    app.state.settings.auth_enabled = False
    with TestClient(app) as test_client:
        yield test_client, db


def test_ping():
    with client() as (c, _):
        response = c.get("/ping")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert "X-RateLimit-Limit" in response.headers


def test_episode_success_and_not_found():
    with client() as (c, _):
        ok = c.get("/episodes/1")
        assert ok.status_code == 200
        assert ok.json()["episode_number"] == 1

        missing = c.get("/episodes/999999")
        assert missing.status_code == 404
        assert missing.headers["content-type"].startswith("application/problem+json")


def test_episode_validation_maps_to_400():
    with client() as (c, _):
        response = c.get("/episodes/0")
        assert response.status_code == 400
        assert response.json()["code"] == "bad_request"


def test_episode_query_contract():
    with client() as (c, db):
        response = c.get(
            "/episodes",
            params={
                "page": 2,
                "limit": 10,
                "genre": "Mystery",
                "sort": "broadcast_date",
                "order": "desc",
            },
        )
        assert response.status_code == 200
        assert response.json()["pagination"]["page"] == 2
        sql, params = db.calls[-1]
        assert "api.get_episodes" in sql
        assert params[0] == 2
        assert params[1] == 10
        assert params[4] == "Mystery"
        assert params[7] == "broadcast_date"
        assert params[8] == "desc"


def test_search_shape():
    with client() as (c, _):
        response = c.get("/search", params={"q": "ghost"})
        assert response.status_code == 200
        assert set(response.json()["data"]) == {"episodes", "cast", "writers"}


def test_protected_users_with_auth_disabled():
    with client() as (c, _):
        response = c.get("/users/1")
        assert response.status_code == 200
        assert response.json()["id"] == 1

        updated = c.patch("/users/1", json={"first_name": "Updated"})
        assert updated.status_code == 200
        assert updated.json()["first_name"] == "Updated"

        deleted = c.delete("/users/1")
        assert deleted.status_code == 204


def test_openapi_document_is_repository_contract():
    with client() as (c, _):
        response = c.get("/openapi.json")
        assert response.status_code == 200
        document = response.json()
        assert document["openapi"] == "3.0.3"
        assert "/episodes" in document["paths"]
        assert "/users/{userId}" in document["paths"]
