from pathlib import Path

from cbsrmt_api.audio_library import discover_audio_files, sync_audio_library


class FakeDatabase:
    def __init__(self, existing_episodes):
        self.existing_episodes = set(existing_episodes)
        self.registered = []

    def scalar_json(self, sql, params=()):
        if "api.get_episode" in sql:
            episode_number = params[0]
            if episode_number not in self.existing_episodes:
                return None
            return {"episode_number": episode_number}

        if "admin.set_episode_audio" in sql:
            self.registered.append(params)
            return {"episode_number": params[0], "stream_url": params[1]}

        raise AssertionError(f"Unexpected SQL: {sql}")


def test_discover_audio_files_accepts_four_digit_mp3_names(tmp_path: Path):
    (tmp_path / "0523.mp3").write_bytes(b"audio")
    (tmp_path / "0001.MP3").write_bytes(b"audio")
    (tmp_path / "523.mp3").write_bytes(b"audio")
    (tmp_path / "notes.txt").write_text("ignore")

    files = discover_audio_files(tmp_path, "http://127.0.0.1:8000/audio/")

    assert [item.episode_number for item in files] == [1, 523]
    assert files[0].stream_url == "http://127.0.0.1:8000/audio/0001.MP3"
    assert files[1].stream_url == "http://127.0.0.1:8000/audio/0523.mp3"


def test_sync_audio_library_registers_existing_episodes_and_skips_unknown(tmp_path: Path):
    (tmp_path / "0523.mp3").write_bytes(b"audio")
    (tmp_path / "0999.mp3").write_bytes(b"audio")

    database = FakeDatabase(existing_episodes={523})
    result = sync_audio_library(
        database,
        tmp_path,
        "http://127.0.0.1:8000/audio",
    )

    assert result["discovered"] == 2
    assert result["registered"] == 1
    assert result["registered_episodes"] == [523]
    assert result["missing_episodes"] == [999]
    assert database.registered == [
        (523, "http://127.0.0.1:8000/audio/0523.mp3", None, "audio/mpeg")
    ]


def test_discover_audio_files_requires_existing_directory(tmp_path: Path):
    missing = tmp_path / "missing"

    try:
        discover_audio_files(missing, "http://127.0.0.1:8000/audio")
    except FileNotFoundError as exc:
        assert str(missing) in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError")
