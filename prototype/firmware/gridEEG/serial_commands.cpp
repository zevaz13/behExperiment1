#include <Arduino.h>

#include "serial_commands.h"
#include "config.h"
#include "trial.h"
#include "settings.h"

namespace {

// One assignment: "<name> <value>", e.g. "trialLengthMs 2500".
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

// "<name> <value>[, <name> <value>...]".
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
      " minRed=" + String(settingsMinRed()) +
      " maxRed=" + String(settingsMaxRed()) +
      " minGreen=" + String(settingsMinGreen()) +
      " maxGreen=" + String(settingsMaxGreen()) +
      " trialLengthMs=" + String(settingsTrialLengthMs()) +
      " interTrialWaitMs=" + String(settingsInterTrialWaitMs()) +
      " baselinesStart=" + String(settingsBaselinesStart()) +
      " baselinesEnd=" + String(settingsBaselinesEnd()) +
      " order=" + String(settingsOrder()));
}

void handleGridStart(const String& command) {
  if (trialIsActive()) {
    Serial.println("Grid already running");
    return;
  }
  // Optional order argument after "GRIDSTART"; falls back to the order setting.
  int order = settingsOrder();
  String arg = command.substring(9);
  arg.trim();
  if (arg.length() > 0) {
    order = arg.toInt();
  }
  trialStart(order);
  Serial.println("Grid started (order " + String(constrain(order, 1, 4)) + ")");
}

}  // namespace

void serialCommandsInit() {
  Serial.begin(kSerialBaud);
  while (!Serial) {
    // wait for the host to open the serial connection
  }
  Serial.println("Grid EEG ready. Send GRIDSTART [order] to begin, GRIDSTOP to abort.");
}

void serialCommandsPoll() {
  if (Serial.available() <= 0) {
    return;
  }

  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command == "GRIDSTART" || command.startsWith("GRIDSTART ")) {
    handleGridStart(command);
  } else if (command == "GRIDSTOP") {
    if (trialIsActive()) {
      trialStop();
      Serial.println("Grid stopped");
    }
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
