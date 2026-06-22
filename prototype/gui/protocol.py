"""Parsing/building for the Teensy serial protocol.

See ../../docs/configure.md for the command and dataframe reference.
"""

from __future__ import annotations

from dataclasses import dataclass

# Field order matches docs/configure.md: TriggerCue@TrialNumber@Amber@red@green@Press
_DATAFRAME_FIELD_COUNT = 6

SETTING_NAMES = (
    "flickerFrequencyHz",
    "amberValue",
    "maxRed",
    "maxGreen",
    "minRed",
    "minGreen",
)


@dataclass(frozen=True)
class DataFrame:
    trigger_cue: int
    trial_number: int
    amber: int
    red: int
    green: int
    press: int


@dataclass(frozen=True)
class Settings:
    mode: str
    flicker_frequency_hz: int
    amber_value: int
    max_red: int
    max_green: int
    min_red: int
    min_green: int


def parse_dataframe(line: str) -> DataFrame | None:
    """Parses a telemetry/result line. Returns None if it isn't one."""
    fields = line.strip().split("@")
    if len(fields) != _DATAFRAME_FIELD_COUNT:
        return None
    try:
        trigger_cue, trial_number, amber, red, green, press = (int(f) for f in fields)
    except ValueError:
        return None
    return DataFrame(trigger_cue, trial_number, amber, red, green, press)


def parse_get_response(line: str) -> Settings | None:
    """Parses the response to GET: "mode=ADVANCED flickerFrequencyHz=20 ..."."""
    if not line.startswith("mode="):
        return None
    values: dict[str, str] = {}
    for token in line.strip().split(" "):
        if "=" not in token:
            return None
        key, _, value = token.partition("=")
        values[key] = value
    try:
        return Settings(
            mode=values["mode"],
            flicker_frequency_hz=int(values["flickerFrequencyHz"]),
            amber_value=int(values["amberValue"]),
            max_red=int(values["maxRed"]),
            max_green=int(values["maxGreen"]),
            min_red=int(values["minRed"]),
            min_green=int(values["minGreen"]),
        )
    except (KeyError, ValueError):
        return None


def build_set_command(values: dict[str, int]) -> str:
    """Builds a multi-assignment SET command, e.g. "SET maxRed 2800, amberValue 500"."""
    assignments = ", ".join(f"{name} {value}" for name, value in values.items())
    return f"SET {assignments}"
