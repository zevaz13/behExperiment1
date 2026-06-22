#include <Arduino.h>

#include "serial_commands.h"
#include "config.h"
#include "trial.h"

namespace {
const char* kStartCommand = "START";
const char* kStopCommand  = "STOP";
}  // namespace

void serialCommandsInit() {
  Serial.begin(kSerialBaud);
  while (!Serial) {
    // wait for the host to open the serial connection
  }
  Serial.println("Teensy ready. Send START to begin a trial, STOP to abort.");
}

void serialCommandsPoll() {
  if (Serial.available() <= 0) {
    return;
  }

  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command == kStartCommand && !trialIsActive()) {
    trialStart();
    Serial.println("Trial started");
  } else if (command == kStopCommand && trialIsActive()) {
    trialStop();
    Serial.println("Trial stopped");
  }
}
