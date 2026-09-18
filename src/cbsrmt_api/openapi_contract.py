from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = ROOT / "openapi.yaml"


def load_contract() -> dict[str, Any]:
    with OPENAPI_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def openapi_json_bytes() -> bytes:
    return json.dumps(load_contract(), separators=(",", ":")).encode("utf-8")
