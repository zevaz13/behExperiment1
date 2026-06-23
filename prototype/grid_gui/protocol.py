"""Parsing/building for the grid firmware's serial protocol.

See ../../docs/grid-configure.md for the command and dataframe reference.
"""

from __future__ import annotations

from dataclasses import dataclass

# Frame: TriggerCue@StimNumber@Amber@Red@Green@Phase
_DATAFRAME_FIELD_COUNT = 6

PHASE_BASELINE = 0
PHASE_STIMULUS = 1
PHASE_INTERTRIAL = 2

# SET names, in the firmware's GET output order.
SETTING_NAMES = (
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
class GridFrame:
    trigger_cue: int
    stim_number: int
    amber: int
    red: int
    green: int
    phase: int


@dataclass(frozen=True)
class Settings:
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


def parse_dataframe(line: str) -> GridFrame | None:
    """Parses a grid trial frame. Returns None if it isn't one."""
    fields = line.strip().split("@")
    if len(fields) != _DATAFRAME_FIELD_COUNT:
        return None
    try:
        trigger_cue, stim_number, amber, red, green, phase = (int(f) for f in fields)
    except ValueError:
        return None
    return GridFrame(trigger_cue, stim_number, amber, red, green, phase)


def parse_get_response(line: str) -> Settings | None:
    """Parses the response to GET: "mode=DEFAULT flickerFrequencyHz=10 ..."."""
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


def build_set_command(values: dict[str, int]) -> str:
    """Builds a multi-assignment SET command, e.g. "SET trialLengthMs 2500, order 2"."""
    assignments = ", ".join(f"{name} {value}" for name, value in values.items())
    return f"SET {assignments}"
