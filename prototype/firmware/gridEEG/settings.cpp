#include "settings.h"
#include "config.h"

namespace {

Mode currentMode = Mode::Default;

unsigned int flickerFrequencyHz = kFlickerFrequencyHz;
unsigned int amberValue         = kAmberValue;
unsigned int minRed             = kMinRed;
unsigned int maxRed             = kMaxRed;
unsigned int minGreen           = kMinGreen;
unsigned int maxGreen           = kMaxGreen;
unsigned int trialLengthMs      = kTrialLengthMs;
unsigned int interTrialWaitMs   = kInterTrialWaitMs;
unsigned int baselinesStart     = kBaselinesStart;
unsigned int baselinesEnd       = kBaselinesEnd;
unsigned int order              = kOrder;

void resetToDefaults() {
  flickerFrequencyHz = kFlickerFrequencyHz;
  amberValue         = kAmberValue;
  minRed             = kMinRed;
  maxRed             = kMaxRed;
  minGreen           = kMinGreen;
  maxGreen           = kMaxGreen;
  trialLengthMs      = kTrialLengthMs;
  interTrialWaitMs   = kInterTrialWaitMs;
  baselinesStart     = kBaselinesStart;
  baselinesEnd       = kBaselinesEnd;
  order              = kOrder;
}

}  // namespace

void settingsInit() {
  currentMode = Mode::Default;
  resetToDefaults();
}

Mode settingsMode() {
  return currentMode;
}

void settingsSetMode(Mode mode) {
  currentMode = mode;
  if (mode == Mode::Default) {
    resetToDefaults();
  }
}

bool settingsTrySet(const String& name, long value) {
  if (currentMode != Mode::Advanced) {
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

unsigned int settingsFlickerFrequencyHz() { return flickerFrequencyHz; }
unsigned int settingsAmberValue()         { return amberValue; }
unsigned int settingsMinRed()             { return minRed; }
unsigned int settingsMaxRed()             { return maxRed; }
unsigned int settingsMinGreen()           { return minGreen; }
unsigned int settingsMaxGreen()           { return maxGreen; }
unsigned int settingsTrialLengthMs()      { return trialLengthMs; }
unsigned int settingsInterTrialWaitMs()   { return interTrialWaitMs; }
unsigned int settingsBaselinesStart()     { return baselinesStart; }
unsigned int settingsBaselinesEnd()       { return baselinesEnd; }
unsigned int settingsOrder()              { return order; }
