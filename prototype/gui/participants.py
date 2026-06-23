"""Per-folder participant database (participants.csv) and session file naming.

The database lives inside the chosen save folder, one CSV row per session;
the participants in that folder are the distinct subject IDs across its rows.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from protocol import Settings

GROUPS = ("HC", "PD", "MD", "Protan", "Deutan", "other")
DEFAULT_GROUP = "HC"

_DB_NAME = "participants.csv"
# Stimulator configuration columns, so each session records the settings it
# ran with (one column per setting, matching the GET field names).
_CONFIG_FIELDNAMES = ["mode", "flickerFrequencyHz", "amberValue", "maxRed", "maxGreen", "minRed", "minGreen"]
_FIELDNAMES = ["sub_id", "group", "session", "file", "datetime"] + _CONFIG_FIELDNAMES


@dataclass(frozen=True)
class Participant:
    sub_id: str
    group: str


def _config_columns(settings: Settings) -> dict[str, object]:
    return {
        "mode": settings.mode,
        "flickerFrequencyHz": settings.flicker_frequency_hz,
        "amberValue": settings.amber_value,
        "maxRed": settings.max_red,
        "maxGreen": settings.max_green,
        "minRed": settings.min_red,
        "minGreen": settings.min_green,
    }


def _db_path(folder: Path) -> Path:
    return folder / _DB_NAME


def read_participants(folder: Path) -> list[Participant]:
    """Distinct participants recorded in the folder, in first-seen order.
    Empty if the folder has no database yet."""
    path = _db_path(folder)
    if not path.exists():
        return []
    groups: dict[str, str] = {}
    with path.open(newline="") as db_file:
        for row in csv.DictReader(db_file):
            groups.setdefault(row["sub_id"], row["group"])
    return [Participant(sub_id, group) for sub_id, group in groups.items()]


def session_file_name(sub_id: str, session: int) -> str:
    return f"{sub_id}_R{session}.txt"


def next_session_number(folder: Path, sub_id: str) -> int:
    """First session index whose file doesn't already exist, so a new session
    never overwrites an older one (matches the legacy GUI's scan)."""
    session = 1
    while (folder / session_file_name(sub_id, session)).exists():
        session += 1
    return session


def record_session(
    folder: Path, participant: Participant, session: int, file_name: str, settings: Settings
) -> None:
    """Append one session row (with the stimulator configuration it ran with),
    writing the header if the database is new."""
    path = _db_path(folder)
    is_new = not path.exists()
    with path.open("a", newline="") as db_file:
        writer = csv.DictWriter(db_file, fieldnames=_FIELDNAMES)
        if is_new:
            writer.writeheader()
        writer.writerow(
            {
                "sub_id": participant.sub_id,
                "group": participant.group,
                "session": session,
                "file": file_name,
                "datetime": datetime.now().isoformat(timespec="seconds"),
                **_config_columns(settings),
            }
        )
