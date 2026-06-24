"""Parsing/building for the combined firmware's serial protocol.

See ../../docs/experimentStimControl-configure.md for the command and
dataframe reference. Behavioral and grid each keep their own dataclasses and
SET/GET shapes -- the only thing shared is the underlying frame/key-value
parsing logic.
"""

from __future__ import annotations

from dataclasses import dataclass

# Both frame shapes are TriggerCue@<n>@Amber@Red@Green@<n>.
_DATAFRAME_FIELD_COUNT = 6

PHASE_BASELINE = 0
PHASE_STIMULUS = 1
PHASE_INTERTRIAL = 2

# SET names, in the firmware's GET output order.
BEHAVIORAL_SETTING_NAMES = (
    "flickerFrequencyHz",
    "amberValue",
    "maxRed",
    "maxGreen",
    "minRed",
    "minGreen",
)

GRID_SETTING_NAMES = (
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
)


@dataclass(frozen=True)
class BehavioralFrame:
    trigger_cue: int
    trial_number: int
    amber: int
    red: int
    green: int
    press: int


@dataclass(frozen=True)
class GridFrame:
    trigger_cue: int
    stim_number: int
    amber: int
    red: int
    green: int
    phase: int


@dataclass(frozen=True)
class BehavioralSettings:
    mode: str
    flicker_frequency_hz: int
    amber_value: int
    max_red: int
    max_green: int
    min_red: int
    min_green: int


@dataclass(frozen=True)
class GridSettings:
    mode: str
    flicker_frequency_hz: int
    amber_value: int
    min_red: int
    max_red: int
    min_green: int
    max_green: int
    trial_length_ms: int
    inter_trial_wait_ms: int
    baselines_start: int
    baselines_end: int
    order: int


def _split_dataframe_fields(line: str) -> list[int] | None:
    fields = line.strip().split("@")
    if len(fields) != _DATAFRAME_FIELD_COUNT:
        return None
    try:
        return [int(field) for field in fields]
    except ValueError:
        return None


def parse_behavioral_dataframe(line: str) -> BehavioralFrame | None:
    """Parses a behavioral telemetry/result line. None if it isn't one."""
    fields = _split_dataframe_fields(line)
    if fields is None:
        return None
    return BehavioralFrame(*fields)


def parse_grid_dataframe(line: str) -> GridFrame | None:
    """Parses a grid trial frame. None if it isn't one."""
    fields = _split_dataframe_fields(line)
    if fields is None:
        return None
    return GridFrame(*fields)


def _parse_key_value_line(line: str) -> dict[str, str] | None:
    """Parses "mode=ADVANCED flickerFrequencyHz=20 ..." into a dict."""
    if not line.startswith("mode="):
        return None
    values: dict[str, str] = {}
    for token in line.strip().split(" "):
        if "=" not in token:
            return None
        key, _, value = token.partition("=")
        values[key] = value
    return values


def parse_behavioral_get_response(line: str) -> BehavioralSettings | None:
    """Parses the response to BEHAVIORALGET."""
    values = _parse_key_value_line(line)
    if values is None:
        return None
    try:
        return BehavioralSettings(
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


def parse_grid_get_response(line: str) -> GridSettings | None:
    """Parses the response to GRIDGET."""
    values = _parse_key_value_line(line)
    if values is None:
        return None
    try:
        return GridSettings(
            mode=values["mode"],
            flicker_frequency_hz=int(values["flickerFrequencyHz"]),
            amber_value=int(values["amberValue"]),
            min_red=int(values["minRed"]),
            max_red=int(values["maxRed"]),
            min_green=int(values["minGreen"]),
            max_green=int(values["maxGreen"]),
            trial_length_ms=int(values["trialLengthMs"]),
            inter_trial_wait_ms=int(values["interTrialWaitMs"]),
            baselines_start=int(values["baselinesStart"]),
            baselines_end=int(values["baselinesEnd"]),
            order=int(values["order"]),
        )
    except (KeyError, ValueError):
        return None


def build_set_command(prefix: str, values: dict[str, int]) -> str:
    """Builds e.g. "BEHAVIORALSET maxRed 2800, amberValue 500"."""
    assignments = ", ".join(f"{name} {value}" for name, value in values.items())
    return f"{prefix}SET {assignments}"
