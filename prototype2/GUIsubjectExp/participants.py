"""Per-folder participant databases.

Three CSVs live inside the chosen save folder:
- participants_master.csv   — one row per session, across both experiments
- participants_behavioral.csv — one row per behavioral session with config
- participants_grid.csv       — one row per grid session with config

Session numbers are independent per (subject, experiment) pair.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

GROUPS = ("HC", "PD", "MD", "Protan", "Deutan", "other")
DEFAULT_GROUP = "HC"

_MASTER_DB = "participants_master.csv"
_MASTER_FIELDS = ["sub_id", "group", "experiment", "session", "datetime"]

_BEHAVIORAL_DB = "participants_behavioral.csv"
_BEHAVIORAL_FIELDS = [
    "sub_id", "group", "session", "file", "datetime",
    "mode", "freq", "refAmber", "refCyan",
    "maxA", "minA", "maxB", "minB",
    "trialLength", "interTrialWait",
]

_GRID_DB = "participants_grid.csv"
_GRID_FIELDS = [
    "sub_id", "group", "session", "datetime",
    "mode", "freq", "refAmber", "refCyan",
    "maxA", "minA", "maxB", "minB",
    "nBaselinesStart", "nBaselinesEnd",
    "trialLength", "interTrialWait", "order",
]

_DB_FOR_EXPERIMENT = {"behavioral": _BEHAVIORAL_DB, "grid": _GRID_DB}


def _append_row(path: Path, fieldnames: list[str], row: dict) -> None:
    is_new = not path.exists()
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def list_participants(folder: Path) -> list[tuple[str, str]]:
    """Returns (sub_id, group) pairs from the master CSV, in first-seen order."""
    path = folder / _MASTER_DB
    if not path.exists():
        return []
    seen: dict[str, str] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            seen.setdefault(row["sub_id"], row["group"])
    return list(seen.items())


def session_file_name(sub_id: str, session: int) -> str:
    return f"{sub_id}_R{session}.txt"


def next_session_number(folder: Path, sub_id: str, experiment: str) -> int:
    """First unused session number for this subject and experiment type."""
    path = folder / _DB_FOR_EXPERIMENT[experiment]
    used: set[int] = set()
    if path.exists():
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                if row["sub_id"] == sub_id:
                    used.add(int(row["session"]))
    n = 1
    while n in used:
        n += 1
    return n


def record_behavioral_session(
    folder: Path,
    sub_id: str,
    group: str,
    session: int,
    file_name: str,
    settings: dict,
) -> None:
    """Appends one row to participants_behavioral.csv and participants_master.csv."""
    now = datetime.now().isoformat(timespec="seconds")
    _append_row(
        folder / _BEHAVIORAL_DB,
        _BEHAVIORAL_FIELDS,
        {
            "sub_id": sub_id, "group": group, "session": session,
            "file": file_name, "datetime": now,
            **{k: settings.get(k, "") for k in (
                "mode", "freq", "refAmber", "refCyan",
                "maxA", "minA", "maxB", "minB",
                "trialLength", "interTrialWait",
            )},
        },
    )
    _append_row(
        folder / _MASTER_DB,
        _MASTER_FIELDS,
        {"sub_id": sub_id, "group": group, "experiment": "behavioral",
         "session": session, "datetime": now},
    )


def record_grid_session(
    folder: Path,
    sub_id: str,
    group: str,
    session: int,
    settings: dict,
) -> None:
    """Appends one row to participants_grid.csv and participants_master.csv."""
    now = datetime.now().isoformat(timespec="seconds")
    _append_row(
        folder / _GRID_DB,
        _GRID_FIELDS,
        {
            "sub_id": sub_id, "group": group, "session": session, "datetime": now,
            **{k: settings.get(k, "") for k in (
                "mode", "freq", "refAmber", "refCyan",
                "maxA", "minA", "maxB", "minB",
                "nBaselinesStart", "nBaselinesEnd",
                "trialLength", "interTrialWait", "order",
            )},
        },
    )
    _append_row(
        folder / _MASTER_DB,
        _MASTER_FIELDS,
        {"sub_id": sub_id, "group": group, "experiment": "grid",
         "session": session, "datetime": now},
    )
