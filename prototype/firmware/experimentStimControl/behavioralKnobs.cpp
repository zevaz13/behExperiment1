#include <Arduino.h>
#include <TeensyThreads.h>

#include "behavioralKnobs.h"
#include "behavioralConfig.h"
#include "pins.h"
#include "flicker.h"
#include "behavioralTrial.h"
#include "behavioralSettings.h"

namespace {

int redOffset   = 0;
int greenOffset = 0;

volatile int currentRed   = 0;
volatile int currentGreen = 0;

int averageReading(int pin) {
  long sum = 0;
  for (int i = 0; i < kNumSamples; i++) {
    sum += analogRead(pin);
    delay(kSampleIntervalMs);
  }
  return sum / kNumSamples;
}

// Offsets can be negative (see behavioralKnobsAnchorTo), so wrap with true
// modulo instead of the legacy single-direction subtraction.
int wrapToAdcRange(int value) {
  value %= 4096;
  return value < 0 ? value + 4096 : value;
}

// Suppresses ADC noise jitter near the low end of the output range.
int applyDeadband(int value) {
  return value < kDeadbandThreshold ? 0 : value;
}

// Inverse of map(raw, 0, 4095, minOut, maxOut), clamped to the ADC range.
int rawFromMapped(int mappedValue, int minOut, int maxOut) {
  if (maxOut <= minOut) {
    return 0;
  }
  long raw = (long)(mappedValue - minOut) * 4095 / (maxOut - minOut);
  if (raw < 0)    raw = 0;
  if (raw > 4095) raw = 4095;
  return (int)raw;
}

}  // namespace

void behavioralKnobsInit() {
  analogReadResolution(kAdcResolutionBits);
}

void behavioralKnobsAnchorTo(int targetRed, int targetGreen) {
  int rawRedNow   = analogRead(kRedKnobPin);
  int rawGreenNow = analogRead(kGreenKnobPin);

  int rawRedTarget   = rawFromMapped(targetRed,   behavioralSettingsMinRed(),   behavioralSettingsMaxRed());
  int rawGreenTarget = rawFromMapped(targetGreen, behavioralSettingsMinGreen(), behavioralSettingsMaxGreen());

  redOffset   = rawRedTarget   - rawRedNow;
  greenOffset = rawGreenTarget - rawGreenNow;
}

int behavioralKnobsCurrentRed()   { return currentRed; }
int behavioralKnobsCurrentGreen() { return currentGreen; }

void behavioralKnobsThreadLoop() {
  while (true) {
    if (!behavioralTrialIsSearching()) {
      threads.yield();
      continue;
    }

    int rawRed   = wrapToAdcRange(averageReading(kRedKnobPin)   + redOffset);
    int rawGreen = wrapToAdcRange(averageReading(kGreenKnobPin) + greenOffset);

    currentRed   = applyDeadband(map(rawRed,   0, 4095, behavioralSettingsMinRed(),   behavioralSettingsMaxRed()));
    currentGreen = applyDeadband(map(rawGreen, 0, 4095, behavioralSettingsMinGreen(), behavioralSettingsMaxGreen()));

    flickerSetRedGreen(currentRed, currentGreen);
  }
}
