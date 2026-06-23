#include <TeensyThreads.h>

#include "flicker.h"
#include "behavioralSettings.h"
#include "behavioralKnobs.h"
#include "behavioralTrial.h"
#include "behavioralTelemetry.h"
#include "gridSettings.h"
#include "gridTrial.h"
#include "serial_commands.h"

// Combined firmware for the behavioral (knobs) and grid (EEG) experiments.
// Both run on the same Teensy 4.0/PCB and share the three LEDs, the trigger
// pin, and one flicker driver; only one experiment may be active at a time
// (enforced in serial_commands.cpp). See
// docs/experimentStimControl-configure.md for the full command set.
void setup() {
  serialCommandsInit();
  behavioralSettingsInit();
  gridSettingsInit();
  flickerInit();
  behavioralKnobsInit();
  behavioralTrialInit();
  behavioralTelemetryInit();
  gridTrialInit();

  threads.addThread(behavioralKnobsThreadLoop);
}

void loop() {
  serialCommandsPoll();
  behavioralTelemetryPoll();
  behavioralTrialPoll();
  gridTrialPoll();
}
