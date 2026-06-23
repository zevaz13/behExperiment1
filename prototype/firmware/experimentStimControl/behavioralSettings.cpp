#include "behavioralSettings.h"
#include "behavioralConfig.h"

namespace {

BehavioralMode currentMode = BehavioralMode::Default;

unsigned int flickerFrequencyHz = kBehavioralFlickerFrequencyHz;
unsigned int amberValue         = kBehavioralAmberValue;
unsigned int maxRed             = kBehavioralMaxRed;
unsigned int maxGreen           = kBehavioralMaxGreen;
unsigned int minRed             = kBehavioralMinRed;
unsigned int minGreen           = kBehavioralMinGreen;

void resetToDefaults() {
  flickerFrequencyHz = kBehavioralFlickerFrequencyHz;
  amberValue         = kBehavioralAmberValue;
  maxRed             = kBehavioralMaxRed;
  maxGreen           = kBehavioralMaxGreen;
  minRed             = kBehavioralMinRed;
  minGreen           = kBehavioralMinGreen;
}

}  // namespace

void behavioralSettingsInit() {
  currentMode = BehavioralMode::Default;
  resetToDefaults();
}

BehavioralMode behavioralSettingsMode() {
  return currentMode;
}

void behavioralSettingsSetMode(BehavioralMode mode) {
  currentMode = mode;
  if (mode == BehavioralMode::Default) {
    resetToDefaults();
  }
}

bool behavioralSettingsTrySet(const String& name, long value) {
  if (currentMode != BehavioralMode::Advanced) {
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

unsigned int behavioralSettingsFlickerFrequencyHz() { return flickerFrequencyHz; }
unsigned int behavioralSettingsAmberValue()         { return amberValue; }
unsigned int behavioralSettingsMaxRed()             { return maxRed; }
unsigned int behavioralSettingsMaxGreen()           { return maxGreen; }
unsigned int behavioralSettingsMinRed()             { return minRed; }
unsigned int behavioralSettingsMinGreen()           { return minGreen; }
