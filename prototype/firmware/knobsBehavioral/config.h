#pragma once

// Flicker: amber is always on, red+green are knob-controlled. Both run as
// independent 10 Hz square waves, 50% duty cycle.
constexpr unsigned int kFlickerFrequencyHz  = 10;
constexpr unsigned long kFlickerHalfPeriodUs = 1000000UL / (2 * kFlickerFrequencyHz);

constexpr unsigned long kSerialBaud = 38400;

constexpr int kPwmResolutionBits = 12;
constexpr int kAdcResolutionBits = 12;

// Knob smoothing: average kNumSamples readings, kSampleIntervalMs apart
// (~50 ms window).
constexpr int kNumSamples       = 10;
constexpr int kSampleIntervalMs = 5;

constexpr unsigned int kAmberValue = 2400;
constexpr unsigned int kMaxRed     = 3000;
constexpr unsigned int kMaxGreen   = 2400;

// Per-trial randomized offset added to the raw ADC reading, so the
// knob-to-brightness mapping can't be memorized across trials.
constexpr int kRedOffsetMax   = 1500;
constexpr int kGreenOffsetMax = 500;

constexpr unsigned long kButtonDebounceMs = 250;
