#include <TeensyThreads.h>

#include "settings.h"
#include "flicker.h"
#include "knobs.h"
#include "trial.h"
#include "serial_commands.h"
#include "telemetry.h"

void setup() {
  serialCommandsInit();
  settingsInit();
  flickerInit();
  knobsInit();
  trialInit();
  telemetryInit();

  threads.addThread(knobsThreadLoop);
}

void loop() {
  serialCommandsPoll();
  telemetryPoll();
}
