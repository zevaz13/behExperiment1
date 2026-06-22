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

// Per-trial randomized offset added to the raw ADC reading, so the
// knob-to-brightness mapping can't be memorized across trials.
constexpr int kRedOffsetMax   = 1500;
constexpr int kGreenOffsetMax = 500;

constexpr unsigned long kButtonDebounceMs = 250;

// How often the live trial telemetry is streamed over serial.
constexpr unsigned long kTelemetryIntervalUs = 100000;  // 100 ms
