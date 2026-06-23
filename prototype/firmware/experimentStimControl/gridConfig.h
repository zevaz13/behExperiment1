#pragma once

// Default values for the grid experiment's runtime-configurable settings
// (see gridSettings.h). Flicker: amber and the red+green combination
// alternate as strictly out-of-phase square waves at the same frequency,
// 50% duty cycle.
constexpr unsigned int kGridFlickerFrequencyHz = 10;
constexpr unsigned int kGridAmberValue         = 2400;
constexpr unsigned int kGridMinRed             = 0;
constexpr unsigned int kGridMaxRed             = 3200;
constexpr unsigned int kGridMinGreen           = 0;
constexpr unsigned int kGridMaxGreen           = 2000;

// Each grid stimulus is shown for kGridTrialLengthMs, separated by
// kGridInterTrialWaitMs. kGridBaselinesStart amber-only trials run before
// the grid and kGridBaselinesEnd after it.
constexpr unsigned int kGridTrialLengthMs    = 3000;
constexpr unsigned int kGridInterTrialWaitMs = 750;
constexpr unsigned int kGridBaselinesStart   = 1;
constexpr unsigned int kGridBaselinesEnd     = 1;

// Traversal start corner, 1-4 (see gridSequence.h). Used when GRIDSTART is
// sent without an explicit order argument.
constexpr unsigned int kGridOrder = 1;

// Grid resolution: kNumSteps x kNumSteps stimuli. Compile-time because the
// sequence arrays are statically sized.
constexpr int kNumSteps = 10;
constexpr int kNumStims = kNumSteps * kNumSteps;
