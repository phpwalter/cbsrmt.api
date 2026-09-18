from __future__ import annotations

import json
from pathlib import Path

import yaml


def contract_path() -> Path:
    candidates = (
        Path.cwd() / "openapi.yaml",
        Path(__file__).resolve().parents[2] / "openapi.yaml",
        Path(__file__).resolve().parent / "openapi.yaml",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("openapi.yaml was not found in the application runtime.")


def load_contract() -> dict[str, object]:
    with contract_path().open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def openapi_json_bytes() -> bytes:
    return json.dumps(load_contract(), separators=(",", ":")).encode("utf-8")
