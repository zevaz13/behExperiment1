"""Per-folder participant databases.

Three CSVs live inside the chosen save folder:
- participants_master.csv: one row per session, across either experiment
  (sub_id, group, experiment, session, datetime). This is what the
  Participant screen reads to list "existing participants" regardless of
  which experiment they did before.
- participants_behavioral.csv / participants_grid.csv: one row per session
  for that experiment, plus the stimulator configuration it ran with.
  Session numbers are independent per experiment.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from protocol import BehavioralSettings, GridSettings

GROUPS = ("HC", "PD", "MD", "Protan", "Deutan", "other")
DEFAULT_GROUP = "HC"

_MASTER_DB_NAME = "participants_master.csv"
_MASTER_FIELDNAMES = ["sub_id", "group", "experiment", "session", "datetime"]

_BEHAVIORAL_DB_NAME = "participants_behavioral.csv"
_BEHAVIORAL_CONFIG_FIELDNAMES = [
    "mode",
    "flickerFrequencyHz",
    "amberValue",
    "maxRed",
    "maxGreen",
    "minRed",
    "minGreen",
]
_BEHAVIORAL_FIELDNAMES = ["sub_id", "group", "session", "file", "datetime"] + _BEHAVIORAL_CONFIG_FIELDNAMES

_GRID_DB_NAME = "participants_grid.csv"
_GRID_CONFIG_FIELDNAMES = [
    "mode",
    "flickerFrequencyHz",
    "amberValue",
    "minRed",
    "maxRed",
    "minGreen",
    "maxGreen",
    "trialLengthMs",
    "interTrialWaitMs",
    "baselinesStart",
    "baselinesEnd",
    "order",
]
_GRID_FIELDNAMES = ["sub_id", "group", "session", "datetime"] + _GRID_CONFIG_FIELDNAMES

_EXPERIMENT_DB_NAMES = {"behavioral": _BEHAVIORAL_DB_NAME, "grid": _GRID_DB_NAME}


@dataclass(frozen=True)
class Participant:
    sub_id: str
    group: str


def _behavioral_config_columns(settings: BehavioralSettings) -> dict[str, object]:
    return {
        "mode": settings.mode,
        "flickerFrequencyHz": settings.flicker_frequency_hz,
        "amberValue": settings.amber_value,
        "maxRed": settings.max_red,
        "maxGreen": settings.max_green,
        "minRed": settings.min_red,
        "minGreen": settings.min_green,
    }


def _grid_config_columns(settings: GridSettings) -> dict[str, object]:
    return {
        "mode": settings.mode,
        "flickerFrequencyHz": settings.flicker_frequency_hz,
        "amberValue": settings.amber_value,
        "minRed": settings.min_red,
        "maxRed": settings.max_red,
        "minGreen": settings.min_green,
        "maxGreen": settings.max_green,
        "trialLengthMs": settings.trial_length_ms,
        "interTrialWaitMs": settings.inter_trial_wait_ms,
        "baselinesStart": settings.baselines_start,
        "baselinesEnd": settings.baselines_end,
        "order": settings.order,
    }


def _append_row(path: Path, fieldnames: list[str], row: dict[str, object]) -> None:
    is_new = not path.exists()
    with path.open("a", newline="") as db_file:
        writer = csv.DictWriter(db_file, fieldnames=fieldnames)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def read_participants(folder: Path) -> list[Participant]:
    """Distinct participants recorded in the folder across either
    experiment, in first-seen order. Empty if there's no master database
    yet."""
    path = folder / _MASTER_DB_NAME
    if not path.exists():
        return []
    groups: dict[str, str] = {}
    with path.open(newline="") as db_file:
        for row in csv.DictReader(db_file):
            groups.setdefault(row["sub_id"], row["group"])
    return [Participant(sub_id, group) for sub_id, group in groups.items()]


def session_file_name(sub_id: str, session: int) -> str:
    return f"{sub_id}_R{session}.txt"


def next_session_number(folder: Path, sub_id: str, experiment: str) -> int:
    """First session index not yet used by this subject for this experiment,
    so behavioral and grid sessions are numbered independently per subject."""
    path = folder / _EXPERIMENT_DB_NAMES[experiment]
    used: set[int] = set()
    if path.exists():
        with path.open(newline="") as db_file:
            for row in csv.DictReader(db_file):
                if row["sub_id"] == sub_id:
                    used.add(int(row["session"]))
    session = 1
    while session in used:
        session += 1
    return session


def record_behavioral_session(
    folder: Path, participant: Participant, session: int, file_name: str, settings: BehavioralSettings
) -> None:
    """Appends one row to participants_behavioral.csv and participants_master.csv."""
    now = datetime.now().isoformat(timespec="seconds")
    _append_row(
        folder / _BEHAVIORAL_DB_NAME,
        _BEHAVIORAL_FIELDNAMES,
        {
            "sub_id": participant.sub_id,
            "group": participant.group,
            "session": session,
            "file": file_name,
            "datetime": now,
            **_behavioral_config_columns(settings),
        },
    )
    _append_row(
        folder / _MASTER_DB_NAME,
        _MASTER_FIELDNAMES,
        {
            "sub_id": participant.sub_id,
            "group": participant.group,
            "experiment": "behavioral",
            "session": session,
            "datetime": now,
        },
    )


def record_grid_session(folder: Path, participant: Participant, session: int, settings: GridSettings) -> None:
    """Appends one row to participants_grid.csv and participants_master.csv.

    Grid has no per-session data file (the EEG recording is the data), so
    unlike record_behavioral_session there is no "file" column."""
    now = datetime.now().isoformat(timespec="seconds")
    _append_row(
        folder / _GRID_DB_NAME,
        _GRID_FIELDNAMES,
        {
            "sub_id": participant.sub_id,
            "group": participant.group,
            "session": session,
            "datetime": now,
            **_grid_config_columns(settings),
        },
    )
    _append_row(
        folder / _MASTER_DB_NAME,
        _MASTER_FIELDNAMES,
        {
            "sub_id": participant.sub_id,
            "group": participant.group,
            "experiment": "grid",
            "session": session,
            "datetime": now,
        },
    )
