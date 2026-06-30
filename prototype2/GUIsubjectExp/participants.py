"""Per-folder participant databases.

Three CSVs live inside the chosen save folder:
- participants_master.csv   — one row per session, across both experiments
- participants_behavioral.csv — one row per behavioral session with config
- participants_grid.csv       — one row per grid session with config

Session numbers are independent per (subject, mode) pair, e.g. beh-rg and
beh-bg have separate counters. The counter is the max of existing CSV rows
and existing .txt files in the folder to avoid collisions if the CSV is lost.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

GROUPS = ("HC", "PD", "MD", "Protan", "Deutan", "other")
DEFAULT_GROUP = "HC"

_MASTER_DB = "participants_master.csv"
_MASTER_FIELDS = ["sub_id", "group", "experiment", "mode", "session", "datetime"]

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


def session_file_name(sub_id: str, mode_str: str, session: int) -> str:
    return f"{sub_id}_{mode_str}_R{session}.txt"


def next_session_number(folder: Path, sub_id: str, mode_str: str) -> int:
    """First unused session number for this subject and mode string.

    Scans both the per-experiment CSV and existing .txt files in the folder so
    that the number is safe even if the CSV was deleted or out of sync.
    """
    experiment = "behavioral" if mode_str.startswith("beh") else "grid"
    used: set[int] = set()

    # Scan CSV.
    csv_path = folder / _DB_FOR_EXPERIMENT[experiment]
    if csv_path.exists():
        with csv_path.open(newline="") as f:
            for row in csv.DictReader(f):
                if row["sub_id"] == sub_id and row.get("mode") == mode_str:
                    used.add(int(row["session"]))

    # Scan folder for existing session files.
    pattern = re.compile(
        rf"^{re.escape(sub_id)}_{re.escape(mode_str)}_R(\d+)\.txt$"
    )
    if folder.exists():
        for entry in folder.iterdir():
            m = pattern.match(entry.name)
            if m:
                used.add(int(m.group(1)))

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
    mode = settings.get("mode", "")
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
         "mode": mode, "session": session, "datetime": now},
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
    mode = settings.get("mode", "")
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
         "mode": mode, "session": session, "datetime": now},
    )
