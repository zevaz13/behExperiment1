#pragma once

// Default values for the runtime-configurable grid settings (see settings.h).
// Flicker: amber and the red+green combination alternate as strictly
// out-of-phase square waves at the same frequency, 50% duty cycle.
constexpr unsigned int kFlickerFrequencyHz = 10;
constexpr unsigned int kAmberValue         = 2400;
constexpr unsigned int kMinRed             = 0;
constexpr unsigned int kMaxRed             = 3200;
constexpr unsigned int kMinGreen           = 0;
constexpr unsigned int kMaxGreen           = 2000;

// Each grid stimulus is shown for kTrialLengthMs, separated by
// kInterTrialWaitMs. kBaselinesStart amber-only trials run before the grid
// and kBaselinesEnd after it.
constexpr unsigned int kTrialLengthMs    = 3000;
constexpr unsigned int kInterTrialWaitMs = 750;
constexpr unsigned int kBaselinesStart   = 1;
constexpr unsigned int kBaselinesEnd     = 1;

// Traversal start corner, 1-4 (see sequence.h). Used when GRIDSTART is sent
// without an explicit order argument.
constexpr unsigned int kOrder = 1;

constexpr unsigned long kSerialBaud = 38400;
constexpr int kPwmResolutionBits = 12;

// Grid resolution: kNumSteps x kNumSteps stimuli. Compile-time because the
// sequence arrays are statically sized.
constexpr int kNumSteps = 10;
constexpr int kNumStims = kNumSteps * kNumSteps;
