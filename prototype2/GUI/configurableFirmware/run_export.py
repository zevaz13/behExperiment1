"""Experiment metadata + saved run data (M15-D).

Two save shapes, both plain JSON so they load in one `json.load`:

- `save_run` writes a single self-contained file with the experiment metadata
  and the frame data together (Solid/Behavioral). Read it in Python with:
      d = json.load(open(path))
      meta = d["metadata"]
      df = pandas.DataFrame(d["data"], columns=d["columns"])
- `save_metadata` writes just the metadata as a sidecar next to a `.txt` data
  log that keeps its streaming columnar format (Linear/Grid). The sidecar shares
  the data file's filename stem, so the data links back to its config.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def build_metadata(mode: str, settings: dict, experiment_name: str = "") -> dict:
    """Every config param used for the run, flat, plus provenance fields. The
    provenance keys are written last so they win over any same-named param in
    settings (a GET response carries its own `mode`, for instance)."""
    return {
        **settings,
        "mode": mode,
        "experiment_name": experiment_name,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }


def save_run(path: Path, metadata: dict, columns, rows) -> None:
    obj = {"metadata": metadata, "columns": list(columns), "data": rows}
    path.write_text(json.dumps(obj))


def save_metadata(path: Path, metadata: dict) -> None:
    path.write_text(json.dumps(metadata, indent=2))
