#include <Arduino.h>

#include "serial_commands.h"
#include "config.h"
#include "trial.h"
#include "settings.h"

namespace {

const char* kStartCommand = "START";
const char* kStopCommand  = "STOP";

// "<name> <value>", e.g. "maxRed 2800".
void handleSetCommand(const String& args) {
  int separator = args.indexOf(' ');
  if (separator < 0) {
    Serial.println("SET requires a name and a value");
    return;
  }

  String name = args.substring(0, separator);
  long value  = args.substring(separator + 1).toInt();

  if (settingsTrySet(name, value)) {
    Serial.println("OK " + name + "=" + String(value));
  } else if (settingsMode() != Mode::Advanced) {
    Serial.println("SET requires MODE ADVANCED");
  } else {
    Serial.println("Unknown setting: " + name);
  }
}

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
  } else if (command == "MODE DEFAULT") {
    settingsSetMode(Mode::Default);
    Serial.println("Mode: default");
  } else if (command == "MODE ADVANCED") {
    settingsSetMode(Mode::Advanced);
    Serial.println("Mode: advanced");
  } else if (command.startsWith("SET ")) {
    handleSetCommand(command.substring(4));
  } else {
    Serial.println("Unknown command");
  }
}
