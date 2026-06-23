#pragma once

// Default values for the runtime-configurable settings (see settings.h).
// Flicker: amber is always on, red+green are knob-controlled, both as
// independent square waves at the same frequency, 50% duty cycle.
constexpr unsigned int kFlickerFrequencyHz = 10;
constexpr unsigned int kAmberValue         = 2400;
constexpr unsigned int kMaxRed             = 3000;
constexpr unsigned int kMaxGreen           = 2400;
constexpr unsigned int kMinRed             = 0;
constexpr unsigned int kMinGreen           = 0;

constexpr unsigned long kSerialBaud = 38400;

constexpr int kPwmResolutionBits = 12;
constexpr int kAdcResolutionBits = 12;

// Knob smoothing: average kNumSamples readings, kSampleIntervalMs apart
// (~50 ms window).
constexpr int kNumSamples       = 10;
constexpr int kSampleIntervalMs = 5;

constexpr unsigned long kButtonDebounceMs = 250;

// How often the live trial telemetry is streamed over serial.
constexpr unsigned long kTelemetryIntervalUs = 100000;  // 100 ms

// Acknowledge blink (button press feedback) and inter-search break: all
// three LEDs blink together kAcknowledgeBlinkCount times, then go dark for
// kBreakDurationMs before the next search starts automatically.
constexpr int kAcknowledgeBlinkCount           = 3;
constexpr unsigned long kAcknowledgeBlinkIntervalMs = 80;
constexpr unsigned long kBreakDurationMs       = 2000;

// Each search's starting point is the previous button press's location,
// shifted by a fresh random jump, so it can't be memorized across searches.
// The jump's magnitude is drawn from [kWalkJumpMin, kWalkJumpMax] (same
// range for both channels) with a random sign, so it's always a real move,
// never a negligible one. The very first search of a session starts at the
// interior margin point (see kStartMarginDivisor).
constexpr int kWalkJumpMin = 500;
constexpr int kWalkJumpMax = 1500;

// Search start points are kept this fraction of the range in from each edge:
// margin = (max - min) / kStartMarginDivisor. Anchoring a search to the very
// edge of the range puts the knob's raw ADC reading on the modulo-4096 wrap
// boundary, where a couple of units of noise flip the LEDs between min and
// max. Starting (and clamping every search's target) inside this margin keeps
// the anchored reading clear of that boundary. The participant can still reach
// the full [min, max] range by turning the knob; only the start point is
// constrained.
constexpr int kStartMarginDivisor = 5;

// Mapped red/green readings within this many units of 0 are snapped to
// exactly 0, to suppress ADC noise jitter near the low end of the range.
constexpr int kDeadbandThreshold = 25;
