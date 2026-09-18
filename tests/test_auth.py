from __future__ import annotations

import jwt
from fastapi.testclient import TestClient

from cbsrmt_api.config import get_settings
from cbsrmt_api.main import create_app
from test_api import FakeDatabase


def test_missing_token_is_401(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "jwt_secret", "test-secret")
    monkeypatch.setattr(settings, "auth_algorithms", "HS256")

    app = create_app(database=FakeDatabase())
    with TestClient(app) as client:
        response = client.get("/users")
        assert response.status_code == 401


def test_scope_enforcement(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "jwt_secret", "test-secret")
    monkeypatch.setattr(settings, "auth_algorithms", "HS256")

    token = jwt.encode({"sub": "client", "scope": "read"}, "test-secret", algorithm="HS256")
    app = create_app(database=FakeDatabase())

    with TestClient(app) as client:
        headers = {"Authorization": f"Bearer {token}"}
        read = client.get("/users", headers=headers)
        assert read.status_code == 200

        write = client.patch("/users/1", headers=headers, json={"first_name": "Nope"})
        assert write.status_code == 403
