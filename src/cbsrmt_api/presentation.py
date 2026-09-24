from __future__ import annotations

import re
from typing import Any

_TRAILING_ARTICLE = re.compile(r"^(?P<title>.+?)\s+\[(?P<article>The|An|A)\]\s*$")


def normalize_episode_title(value: str) -> str:
    """Move a trailing bracketed article to the beginning of an episode title."""
    match = _TRAILING_ARTICLE.match(value)
    if match is None:
        return value

    title = match.group("title").strip()
    article = match.group("article")
    return f"{article} {title}"


def normalize_episode_number(value: Any) -> Any:
    """Return episode numbers as canonical integers without leading zeros."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return value


def normalize_episode_titles(value: Any) -> Any:
    """Recursively normalize episode presentation values in API response payloads."""
    if isinstance(value, list):
        return [normalize_episode_titles(item) for item in value]

    if isinstance(value, dict):
        normalized: dict[Any, Any] = {}
        for key, item in value.items():
            if key == "episode_name" and isinstance(item, str):
                normalized[key] = normalize_episode_title(item)
            elif key == "episode_number":
                normalized[key] = normalize_episode_number(item)
            else:
                normalized[key] = normalize_episode_titles(item)
        return normalized

    return value
