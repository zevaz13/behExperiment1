#include "settings.h"
#include "config.h"

namespace {

Mode currentMode = Mode::Default;

unsigned int flickerFrequencyHz = kFlickerFrequencyHz;
unsigned int amberValue         = kAmberValue;
unsigned int maxRed             = kMaxRed;
unsigned int maxGreen           = kMaxGreen;
unsigned int minRed             = kMinRed;
unsigned int minGreen           = kMinGreen;

void resetToDefaults() {
  flickerFrequencyHz = kFlickerFrequencyHz;
  amberValue         = kAmberValue;
  maxRed             = kMaxRed;
  maxGreen           = kMaxGreen;
  minRed             = kMinRed;
  minGreen           = kMinGreen;
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
  } else if (name == "maxRed") {
    maxRed = value;
  } else if (name == "maxGreen") {
    maxGreen = value;
  } else if (name == "minRed") {
    minRed = value;
  } else if (name == "minGreen") {
    minGreen = value;
  } else {
    return false;
  }
  return true;
}

unsigned int settingsFlickerFrequencyHz() { return flickerFrequencyHz; }
unsigned int settingsAmberValue()         { return amberValue; }
unsigned int settingsMaxRed()             { return maxRed; }
unsigned int settingsMaxGreen()           { return maxGreen; }
unsigned int settingsMinRed()             { return minRed; }
unsigned int settingsMinGreen()           { return minGreen; }
