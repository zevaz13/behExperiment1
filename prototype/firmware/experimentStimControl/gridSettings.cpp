#include "gridSettings.h"
#include "gridConfig.h"

namespace {

GridMode currentMode = GridMode::Default;

unsigned int flickerFrequencyHz = kGridFlickerFrequencyHz;
unsigned int amberValue         = kGridAmberValue;
unsigned int minRed             = kGridMinRed;
unsigned int maxRed             = kGridMaxRed;
unsigned int minGreen           = kGridMinGreen;
unsigned int maxGreen           = kGridMaxGreen;
unsigned int trialLengthMs      = kGridTrialLengthMs;
unsigned int interTrialWaitMs   = kGridInterTrialWaitMs;
unsigned int baselinesStart     = kGridBaselinesStart;
unsigned int baselinesEnd       = kGridBaselinesEnd;
unsigned int order              = kGridOrder;

void resetToDefaults() {
  flickerFrequencyHz = kGridFlickerFrequencyHz;
  amberValue         = kGridAmberValue;
  minRed             = kGridMinRed;
  maxRed             = kGridMaxRed;
  minGreen           = kGridMinGreen;
  maxGreen           = kGridMaxGreen;
  trialLengthMs      = kGridTrialLengthMs;
  interTrialWaitMs   = kGridInterTrialWaitMs;
  baselinesStart     = kGridBaselinesStart;
  baselinesEnd       = kGridBaselinesEnd;
  order              = kGridOrder;
}

}  // namespace

void gridSettingsInit() {
  currentMode = GridMode::Default;
  resetToDefaults();
}

GridMode gridSettingsMode() {
  return currentMode;
}

void gridSettingsSetMode(GridMode mode) {
  currentMode = mode;
  if (mode == GridMode::Default) {
    resetToDefaults();
  }
}

bool gridSettingsTrySet(const String& name, long value) {
  if (currentMode != GridMode::Advanced) {
    return false;
  }
  if (name == "flickerFrequencyHz") {
    flickerFrequencyHz = value;
  } else if (name == "amberValue") {
    amberValue = value;
  } else if (name == "minRed") {
    minRed = value;
  } else if (name == "maxRed") {
    maxRed = value;
  } else if (name == "minGreen") {
    minGreen = value;
  } else if (name == "maxGreen") {
    maxGreen = value;
  } else if (name == "trialLengthMs") {
    trialLengthMs = value;
  } else if (name == "interTrialWaitMs") {
    interTrialWaitMs = value;
  } else if (name == "baselinesStart") {
    baselinesStart = value;
  } else if (name == "baselinesEnd") {
    baselinesEnd = value;
  } else if (name == "order") {
    order = constrain(value, 1, 4);
  } else {
    return false;
  }
  return true;
}

unsigned int gridSettingsFlickerFrequencyHz() { return flickerFrequencyHz; }
unsigned int gridSettingsAmberValue()         { return amberValue; }
unsigned int gridSettingsMinRed()             { return minRed; }
unsigned int gridSettingsMaxRed()             { return maxRed; }
unsigned int gridSettingsMinGreen()           { return minGreen; }
unsigned int gridSettingsMaxGreen()           { return maxGreen; }
unsigned int gridSettingsTrialLengthMs()      { return trialLengthMs; }
unsigned int gridSettingsInterTrialWaitMs()   { return interTrialWaitMs; }
unsigned int gridSettingsBaselinesStart()     { return baselinesStart; }
unsigned int gridSettingsBaselinesEnd()       { return baselinesEnd; }
unsigned int gridSettingsOrder()              { return order; }
