#include <Arduino.h>

#include "serial_commands.h"
#include "config.h"
#include "trial.h"
#include "settings.h"

namespace {

const char* kStartCommand = "START";
const char* kStopCommand  = "STOP";

// One assignment: "<name> <value>", e.g. "maxRed 2800".
void applySetting(const String& assignment) {
  int separator = assignment.indexOf(' ');
  if (separator < 0) {
    Serial.println("SET requires a name and a value: " + assignment);
    return;
  }

  String name = assignment.substring(0, separator);
  long value  = assignment.substring(separator + 1).toInt();

  if (settingsTrySet(name, value)) {
    Serial.println("OK " + name + "=" + String(value));
  } else if (settingsMode() != Mode::Advanced) {
    Serial.println("SET requires MODE ADVANCED");
  } else {
    Serial.println("Unknown setting: " + name);
  }
}

// "<name> <value>[, <name> <value>...]", e.g.
// "flickerFrequencyHz 20, amberValue 500".
void handleSetCommand(const String& args) {
  int start = 0;
  while (start < (int)args.length()) {
    int comma = args.indexOf(',', start);
    String assignment = (comma < 0) ? args.substring(start) : args.substring(start, comma);
    assignment.trim();
    if (assignment.length() > 0) {
      applySetting(assignment);
    }
    if (comma < 0) {
      break;
    }
    start = comma + 1;
  }
}

void printCurrentSettings() {
  Serial.println(
      "mode=" + String(settingsMode() == Mode::Advanced ? "ADVANCED" : "DEFAULT") +
      " flickerFrequencyHz=" + String(settingsFlickerFrequencyHz()) +
      " amberValue=" + String(settingsAmberValue()) +
      " maxRed=" + String(settingsMaxRed()) +
      " maxGreen=" + String(settingsMaxGreen()) +
      " minRed=" + String(settingsMinRed()) +
      " minGreen=" + String(settingsMinGreen()));
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
  } else if (command == "GET") {
    printCurrentSettings();
  } else {
    Serial.println("Unknown command");
  }
}
