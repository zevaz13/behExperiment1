#include <Arduino.h>
#include <IntervalTimer.h>

#include "behavioralTelemetry.h"
#include "behavioralConfig.h"
#include "behavioralSettings.h"
#include "behavioralTrial.h"
#include "behavioralKnobs.h"
#include "behavioralDataframe.h"

namespace {

IntervalTimer telemetryTimer;
volatile bool dueToSend = false;

// Keep the ISR itself tiny: just raise a flag. The actual Serial I/O
// happens in behavioralTelemetryPoll(), called from the main loop.
void onTelemetryTick() {
  dueToSend = true;
}

}  // namespace

void behavioralTelemetryInit() {
  telemetryTimer.begin(onTelemetryTick, kTelemetryIntervalUs);
}

void behavioralTelemetryPoll() {
  if (!dueToSend) {
    return;
  }
  dueToSend = false;

  if (!behavioralTrialIsSearching()) {
    return;
  }
  behavioralSendDataFrame(behavioralSettingsAmberValue(), behavioralKnobsCurrentRed(),
                           behavioralKnobsCurrentGreen(), 0, behavioralTrialCurrentNumber());
}
