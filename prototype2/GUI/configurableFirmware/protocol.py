"""Parsing/building for the configurableFirmware serial protocol.

See docs/superpowers/specs/2026-07-01-configurable-firmware-design.md and
docs/prototype2/statusREP.md for the full protocol reference.

Commands (GUI -> Teensy):
    MODE <SOLID|LINEAR|GRID|BEHAVIORAL>
    SET <param> <value>[, <param> <value> ...]
    GET [param]
    START
    STOP
    PRESS   (Solid or Behavioral only, while running)

Frame format (every 100 ms while running):
    FRAME@TrialNumber@Red@Yellow@Green@Blue@Cyan@HUE_R@HUE_G@HUE_B@HUE_CT@HUE_L@LEDA@LEDB@Press@Trigger
    Unused numeric fields are -99. LEDA/LEDB are the assigned LED's name (or "NONE").

GET response (multi-line key=value pairs, complete once a 'mode=' line arrives):
    freq=10
    trialLength=3000
    ...
    mode=SOLID
"""

from __future__ import annotations

_FRAME_PREFIX = "FRAME@"

FRAME_FIELDS = (
    "TrialNumber", "Red", "Yellow", "Green", "Blue", "Cyan",
    "HUE_R", "HUE_G", "HUE_B", "HUE_CT", "HUE_L",
    "LEDA", "LEDB", "Press", "Trigger",
)

# Fields that carry an int; LEDA/LEDB are left as the LED-name string.
_FRAME_INT_FIELDS = tuple(f for f in FRAME_FIELDS if f not in ("LEDA", "LEDB"))


def parse_frame(line: str) -> dict | None:
    """Parses a FRAME@... telemetry line into a dict, or None if not a frame.

    Numeric fields are ints; LEDA/LEDB are the LED name strings (e.g. "RED", or "NONE").
    """
    if not line.startswith(_FRAME_PREFIX):
        return None
    tokens = line[len(_FRAME_PREFIX):].split("@")
    if len(tokens) != len(FRAME_FIELDS):
        return None
    result: dict = dict(zip(FRAME_FIELDS, tokens))
    for field in _FRAME_INT_FIELDS:
        try:
            result[field] = int(result[field])
        except ValueError:
            return None
    return result


def parse_get_response(lines: list[str]) -> dict[str, str] | None:
    """Parses accumulated GET response lines into a flat dict.

    Collects key=value pairs; returns None until the 'mode' key has arrived
    (the firmware always emits it last), meaning the response is incomplete.
    """
    result: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result if "mode" in result else None


def build_mode_command(mode: str) -> str:
    """Builds a MODE command. Example: build_mode_command("SOLID") -> "MODE SOLID"."""
    return f"MODE {mode}"


def build_set_command(params: dict[str, str | int]) -> str:
    """Builds a SET command from param->value pairs, comma-space separated.

    Example: {"LEDA": "RED", "maxA": 3000} -> "SET LEDA RED, maxA 3000"
    """
    return "SET " + ", ".join(f"{k} {v}" for k, v in params.items())
