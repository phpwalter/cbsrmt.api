from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from .config import get_settings
from .db import Database

AUDIO_FILENAME = re.compile(r"^(?P<episode>\d{4})\.mp3$", re.IGNORECASE)


@dataclass(frozen=True)
class AudioFile:
    episode_number: int
    path: Path
    stream_url: str


def discover_audio_files(root: Path, public_base_url: str) -> list[AudioFile]:
    """Return valid four-digit episode MP3s from the configured local directory."""
    if not root.exists():
        raise FileNotFoundError(f"Audio directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Audio path is not a directory: {root}")

    base = public_base_url.rstrip("/")
    files: list[AudioFile] = []

    for path in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file():
            continue

        match = AUDIO_FILENAME.fullmatch(path.name)
        if match is None:
            continue

        episode_number = int(match.group("episode"))
        if episode_number < 1:
            continue

        files.append(
            AudioFile(
                episode_number=episode_number,
                path=path,
                stream_url=f"{base}/{quote(path.name)}",
            )
        )

    return files


def sync_audio_library(database: Database, root: Path, public_base_url: str) -> dict[str, object]:
    """Register local MP3 links in catalog.episode_media through the admin API."""
    discovered = discover_audio_files(root, public_base_url)
    registered: list[int] = []
    missing_episodes: list[int] = []

    for audio_file in discovered:
        episode = database.scalar_json(
            "SELECT api.get_episode(%s)",
            (audio_file.episode_number,),
        )
        if episode is None:
            missing_episodes.append(audio_file.episode_number)
            continue

        database.scalar_json(
            "SELECT admin.set_episode_audio(%s,%s,%s,%s)",
            (
                audio_file.episode_number,
                audio_file.stream_url,
                None,
                "audio/mpeg",
            ),
        )
        registered.append(audio_file.episode_number)

    return {
        "audio_root": str(root),
        "discovered": len(discovered),
        "registered": len(registered),
        "registered_episodes": registered,
        "missing_episodes": missing_episodes,
    }


def run() -> None:
    settings = get_settings()
    if not settings.audio_root:
        raise SystemExit("AUDIO_ROOT is not configured.")

    database = Database(
        settings.database_url,
        settings.database_min_pool,
        settings.database_max_pool,
    )
    database.open()
    try:
        result = sync_audio_library(
            database,
            Path(settings.audio_root).expanduser().resolve(),
            settings.audio_public_base_url,
        )
    finally:
        database.close()

    print(f"Audio root: {result['audio_root']}")
    print(f"MP3 files discovered: {result['discovered']}")
    print(f"Episodes registered: {result['registered']}")

    missing = result["missing_episodes"]
    if missing:
        print("Skipped files with no matching episode: " + ", ".join(str(value) for value in missing))


if __name__ == "__main__":
    run()
