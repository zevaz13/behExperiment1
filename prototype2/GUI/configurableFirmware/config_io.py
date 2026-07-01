"""JSON save/load for Linear/Grid experiment parameter configs."""

from __future__ import annotations

import json
from pathlib import Path


def save_config(path: Path, params: dict) -> None:
    path.write_text(json.dumps(params, indent=2))


def load_config(path: Path) -> dict:
    return json.loads(path.read_text())
