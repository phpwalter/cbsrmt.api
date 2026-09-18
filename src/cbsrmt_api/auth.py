from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    subject: str
    scopes: frozenset[str]
    claims: dict


def _extract_scopes(claims: dict) -> frozenset[str]:
    raw = claims.get("scope", claims.get("scp", []))
    if isinstance(raw, str):
        return frozenset(item for item in raw.split() if item)
    if isinstance(raw, list):
        return frozenset(str(item) for item in raw)
    return frozenset()


def _decode_token(token: str, request: Request) -> dict:
    settings = request.app.state.settings

    options = {"verify_aud": bool(settings.auth_audience)}
    kwargs = {
        "algorithms": settings.algorithms,
        "issuer": settings.auth_issuer,
        "audience": settings.auth_audience,
        "options": options,
    }

    if settings.auth_jwks_url:
        jwks_client = request.app.state.jwks_client
        signing_key = jwks_client.get_signing_key_from_jwt(token).key
        return jwt.decode(token, signing_key, **kwargs)

    if settings.jwt_secret:
        return jwt.decode(token, settings.jwt_secret, **kwargs)

    raise HTTPException(
        status_code=500,
        detail="Authentication is enabled but no JWT verification key source is configured.",
    )


async def require_scopes(request: Request, required: Iterable[str]) -> Principal:
    settings = request.app.state.settings

    if not settings.auth_enabled:
        return Principal(subject="development", scopes=frozenset(required), claims={})

    credentials: HTTPAuthorizationCredentials | None = await bearer(request)
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer authentication is required.")

    try:
        claims = _decode_token(credentials.credentials, request)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Bearer token is invalid.") from exc

    scopes = _extract_scopes(claims)
    missing = set(required) - scopes
    if missing:
        raise HTTPException(
            status_code=403,
            detail=f"Missing required scope(s): {', '.join(sorted(missing))}",
        )

    subject = str(claims.get("sub", ""))
    return Principal(subject=subject, scopes=scopes, claims=claims)


async def require_read(request: Request) -> Principal:
    return await require_scopes(request, {"read"})


async def require_write(request: Request) -> Principal:
    return await require_scopes(request, {"write"})


def issue_local_token(client_id: str, client_secret: str, scope: str, request: Request) -> dict:
    settings = request.app.state.settings
    if not settings.jwt_secret or not settings.oauth_client_id or not settings.oauth_client_secret:
        raise HTTPException(status_code=503, detail="Local OAuth token issuance is not configured.")
    if client_id != settings.oauth_client_id or client_secret != settings.oauth_client_secret:
        raise HTTPException(status_code=401, detail="Invalid client credentials.")

    import time

    now = int(time.time())
    requested = frozenset(item for item in scope.split() if item)
    allowed = {"read", "write"}
    if not requested:
        requested = frozenset({"read"})
    if not requested.issubset(allowed):
        raise HTTPException(status_code=400, detail="Unsupported scope requested.")

    claims = {
        "sub": client_id,
        "scope": " ".join(sorted(requested)),
        "iat": now,
        "exp": now + settings.oauth_token_ttl_seconds,
    }
    if settings.auth_issuer:
        claims["iss"] = settings.auth_issuer
    if settings.auth_audience:
        claims["aud"] = settings.auth_audience

    token = jwt.encode(
        claims,
        settings.jwt_secret,
        algorithm=settings.oauth_token_algorithm,
    )
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": settings.oauth_token_ttl_seconds,
        "scope": claims["scope"],
    }
