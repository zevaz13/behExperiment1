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
// shifted by a fresh random offset within +/- this range, so it can't be
// memorized across searches. The very first search of a session starts at
// (0, 0).
constexpr int kWalkJitterRed   = 1000;
constexpr int kWalkJitterGreen = 1000;
