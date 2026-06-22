#include <TeensyThreads.h>

#include "flicker.h"
#include "knobs.h"
#include "trial.h"
#include "serial_commands.h"

void setup() {
  serialCommandsInit();
  flickerInit();
  knobsInit();
  trialInit();

  threads.addThread(knobsThreadLoop);
}

void loop() {
  serialCommandsPoll();
}
