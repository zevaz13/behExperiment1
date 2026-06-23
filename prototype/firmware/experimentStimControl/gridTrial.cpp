#include <Arduino.h>

#include "gridTrial.h"
#include "gridConfig.h"
#include "pins.h"
#include "flicker.h"
#include "gridSequence.h"
#include "gridSettings.h"
#include "gridDataframe.h"

namespace {

enum class State { Idle, Active, Intertrial };

State state = State::Idle;
int trialIndex = 0;             // 0 .. totalTrials-1
int totalTrials = 0;
int runBaselinesStart = 0;      // snapshot at start, so the schedule is stable
unsigned long phaseStartMs = 0;

bool isBaseline(int t) {
  return t < runBaselinesStart || t >= runBaselinesStart + kNumStims;
}

int gridIndexOf(int t) {
  return t - runBaselinesStart;
}

void beginActive(int t) {
  state = State::Active;
  phaseStartMs = millis();
  digitalWrite(kTriggerPin, HIGH);

  if (isBaseline(t)) {
    flickerSteadyAmber(gridSettingsAmberValue());
    gridSendDataFrame(1, 0, gridSettingsAmberValue(), 0, 0, kGridPhaseBaseline);
  } else {
    int i = gridIndexOf(t);
    int red   = gridSequenceRed(i);
    int green = gridSequenceGreen(i);
    flickerStart(red, green, gridSettingsAmberValue(), gridSettingsFlickerFrequencyHz());
    gridSendDataFrame(1, i + 1, gridSettingsAmberValue(), red, green, kGridPhaseStimulus);
  }
}

void beginIntertrial(int t) {
  state = State::Intertrial;
  phaseStartMs = millis();
  digitalWrite(kTriggerPin, LOW);
  flickerStop();
  int stim = isBaseline(t) ? 0 : gridIndexOf(t) + 1;
  gridSendDataFrame(0, stim, 0, 0, 0, kGridPhaseIntertrial);
}

}  // namespace

void gridTrialInit() {
  digitalWrite(kTriggerPin, LOW);
}

void gridTrialStart(int order) {
  runBaselinesStart = gridSettingsBaselinesStart();
  totalTrials = runBaselinesStart + kNumStims + gridSettingsBaselinesEnd();
  gridSequenceBuild(constrain(order, 1, 4),
                    gridSettingsMinRed(), gridSettingsMaxRed(),
                    gridSettingsMinGreen(), gridSettingsMaxGreen());
  trialIndex = 0;
  beginActive(trialIndex);
}

void gridTrialStop() {
  state = State::Idle;
  digitalWrite(kTriggerPin, LOW);
  flickerStop();
}

bool gridTrialIsActive() {
  return state != State::Idle;
}

void gridTrialPoll() {
  if (state == State::Active) {
    if (millis() - phaseStartMs >= gridSettingsTrialLengthMs()) {
      beginIntertrial(trialIndex);
    }
  } else if (state == State::Intertrial) {
    if (millis() - phaseStartMs >= gridSettingsInterTrialWaitMs()) {
      trialIndex++;
      if (trialIndex >= totalTrials) {
        gridTrialStop();
        Serial.println("GRID DONE");
      } else {
        beginActive(trialIndex);
      }
    }
  }
}
