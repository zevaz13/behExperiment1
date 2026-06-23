#include "settings.h"
#include "flicker.h"
#include "trial.h"
#include "serial_commands.h"

// Grid (EEG) experiment firmware. Presents a grid of red/green stimuli,
// flickered out of phase with amber at the configured frequency, pulsing the
// trigger pin for EEG synchronization. No knobs or button: the sequence is
// presented automatically. See docs/grid-configure.md for the command set.
void setup() {
  serialCommandsInit();
  settingsInit();
  flickerInit();
  trialInit();
}

void loop() {
  serialCommandsPoll();
  trialPoll();
}
