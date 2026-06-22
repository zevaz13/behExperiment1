#include <Arduino.h>
#include <IntervalTimer.h>

#include "telemetry.h"
#include "config.h"
#include "settings.h"
#include "trial.h"
#include "knobs.h"
#include "dataframe.h"

namespace {

IntervalTimer telemetryTimer;
volatile bool dueToSend = false;

// Keep the ISR itself tiny: just raise a flag. The actual Serial I/O
// happens in telemetryPoll(), called from the main loop.
void onTelemetryTick() {
  dueToSend = true;
}

}  // namespace

void telemetryInit() {
  telemetryTimer.begin(onTelemetryTick, kTelemetryIntervalUs);
}

void telemetryPoll() {
  if (!dueToSend) {
    return;
  }
  dueToSend = false;

  if (!trialIsSearching()) {
    return;
  }
  sendDataFrame(settingsAmberValue(), knobsCurrentRed(), knobsCurrentGreen(), 0, trialCurrentNumber());
}
