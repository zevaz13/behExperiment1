"""Parsing/building for the subjectExperiment firmware's serial protocol.

See docs/prototype2/prototype2-subjectExperiment-gui-requirements.md for
the full protocol reference.

Frame format (every 100 ms while running):
    &@STIM:<n>,Mode:<RG|BG>,RED:<v>,GREEN:<v>,BLUE:<v>,AMBER:<v>,CYAN:<v>,TRIG:<0|1>%!

Press event:
    RESP,Trial:<n>,A:<primaryVal>,B:<greenVal>

GET response (multi-line, complete when 'mode=' line received):
    freq=10
    refAmber=2400
    ...
    mode=beh-rg
    # comment line (ignored)
"""

from __future__ import annotations

_FRAME_PREFIX = "&@"
_FRAME_SUFFIX = "%!"

# All numeric fields in a stream frame.
_FRAME_INT_FIELDS = ("STIM", "RED", "GREEN", "BLUE", "AMBER", "CYAN", "TRIG")

# Firmware GET response keys, in the order the firmware emits them.
GET_KEYS = (
    "freq", "refAmber", "refCyan",
    "maxA", "minA", "maxB", "minB",
    "nBaselinesStart", "nBaselinesEnd",
    "trialLength", "interTrialWait", "order",
)


def parse_get_response(lines: list[str]) -> dict[str, str] | None:
    """Parses accumulated GET response lines into a flat dict.

    Collects key=value pairs; ignores blank lines and comment lines (#).
    Returns None if the required 'mode' key was not found, indicating the
    response is incomplete.
    """
    result: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result if "mode" in result else None


def parse_stream_frame(line: str) -> dict | None:
    """Parses a &@...%! telemetry frame into a dict. Returns None if not a frame.

    Numeric fields (STIM, RED, GREEN, BLUE, AMBER, CYAN, TRIG) are ints;
    'Mode' is a str ('RG' or 'BG').
    """
    if not (line.startswith(_FRAME_PREFIX) and line.endswith(_FRAME_SUFFIX)):
        return None
    body = line[len(_FRAME_PREFIX): -len(_FRAME_SUFFIX)]
    result: dict = {}
    for token in body.split(","):
        if ":" not in token:
            return None
        key, _, value = token.partition(":")
        result[key] = value
    if "Mode" not in result:
        return None
    for field in _FRAME_INT_FIELDS:
        if field not in result:
            return None
        try:
            result[field] = int(result[field])
        except ValueError:
            return None
    return result


def parse_resp(line: str) -> tuple[int, int, int] | None:
    """Parses a RESP,Trial:n,A:v,B:v line. Returns (trial, A, B) or None."""
    if not line.startswith("RESP,"):
        return None
    try:
        parts = {}
        for tok in line[5:].split(","):
            k, _, v = tok.partition(":")
            parts[k] = v
        return int(parts["Trial"]), int(parts["A"]), int(parts["B"])
    except (ValueError, KeyError):
        return None


def build_batch_command(params: dict[str, int]) -> str:
    """Builds a semicolon-separated batch config command.

    Example: {'freq': 10, 'maxA': 3200} -> 'freq=10;maxA=3200'
    """
    return ";".join(f"{k}={v}" for k, v in params.items())
