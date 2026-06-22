#include <Arduino.h>
#include <TeensyThreads.h>

#include "knobs.h"
#include "config.h"
#include "pins.h"
#include "flicker.h"
#include "trial.h"

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

// Preserves the legacy wraparound behavior for offset readings that spill
// past the 12-bit ADC range.
int wrapToAdcRange(int value) {
  return value > 4095 ? value - 4095 : value;
}

}  // namespace

void knobsInit() {
  analogReadResolution(kAdcResolutionBits);
}

void knobsRandomizeOffsets() {
  redOffset   = random(0, kRedOffsetMax);
  greenOffset = random(0, kGreenOffsetMax);
}

int knobsCurrentRed()   { return currentRed; }
int knobsCurrentGreen() { return currentGreen; }

void knobsThreadLoop() {
  while (true) {
    if (!trialIsActive()) {
      threads.yield();
      continue;
    }

    int rawRed   = wrapToAdcRange(averageReading(kRedKnobPin)   + redOffset);
    int rawGreen = wrapToAdcRange(averageReading(kGreenKnobPin) + greenOffset);

    currentRed   = map(rawRed,   0, 4095, 0, kMaxRed);
    currentGreen = map(rawGreen, 0, 4095, 0, kMaxGreen);

    flickerSetRedGreen(currentRed, currentGreen);
  }
}
