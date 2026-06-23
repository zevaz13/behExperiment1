#include <Arduino.h>

#include "serial_commands.h"
#include "config.h"
#include "behavioralTrial.h"
#include "behavioralSettings.h"
#include "gridTrial.h"
#include "gridSettings.h"

namespace {

// One assignment: "<name> <value>", e.g. "maxRed 2800".
void applySetting(const String& assignment, bool (*trySet)(const String&, long), bool advancedNow) {
  int separator = assignment.indexOf(' ');
  if (separator < 0) {
    Serial.println("SET requires a name and a value: " + assignment);
    return;
  }

  String name = assignment.substring(0, separator);
  long value  = assignment.substring(separator + 1).toInt();

  if (trySet(name, value)) {
    Serial.println("OK " + name + "=" + String(value));
  } else if (!advancedNow) {
    Serial.println("SET requires MODE ADVANCED");
  } else {
    Serial.println("Unknown setting: " + name);
  }
}

// "<name> <value>[, <name> <value>...]", e.g.
// "flickerFrequencyHz 20, amberValue 500".
void handleSetCommand(const String& args, bool (*trySet)(const String&, long), bool advancedNow) {
  int start = 0;
  while (start < (int)args.length()) {
    int comma = args.indexOf(',', start);
    String assignment = (comma < 0) ? args.substring(start) : args.substring(start, comma);
    assignment.trim();
    if (assignment.length() > 0) {
      applySetting(assignment, trySet, advancedNow);
    }
    if (comma < 0) {
      break;
    }
    start = comma + 1;
  }
}

void printBehavioralSettings() {
  Serial.println(
      "mode=" + String(behavioralSettingsMode() == BehavioralMode::Advanced ? "ADVANCED" : "DEFAULT") +
      " flickerFrequencyHz=" + String(behavioralSettingsFlickerFrequencyHz()) +
      " amberValue=" + String(behavioralSettingsAmberValue()) +
      " maxRed=" + String(behavioralSettingsMaxRed()) +
      " maxGreen=" + String(behavioralSettingsMaxGreen()) +
      " minRed=" + String(behavioralSettingsMinRed()) +
      " minGreen=" + String(behavioralSettingsMinGreen()));
}

void printGridSettings() {
  Serial.println(
      "mode=" + String(gridSettingsMode() == GridMode::Advanced ? "ADVANCED" : "DEFAULT") +
      " flickerFrequencyHz=" + String(gridSettingsFlickerFrequencyHz()) +
      " amberValue=" + String(gridSettingsAmberValue()) +
      " minRed=" + String(gridSettingsMinRed()) +
      " maxRed=" + String(gridSettingsMaxRed()) +
      " minGreen=" + String(gridSettingsMinGreen()) +
      " maxGreen=" + String(gridSettingsMaxGreen()) +
      " trialLengthMs=" + String(gridSettingsTrialLengthMs()) +
      " interTrialWaitMs=" + String(gridSettingsInterTrialWaitMs()) +
      " baselinesStart=" + String(gridSettingsBaselinesStart()) +
      " baselinesEnd=" + String(gridSettingsBaselinesEnd()) +
      " order=" + String(gridSettingsOrder()));
}

void handleBehavioralStart() {
  if (gridTrialIsActive()) {
    Serial.println("Grid trial active");
    return;
  }
  if (behavioralTrialIsActive()) {
    return;
  }
  behavioralTrialStart();
  Serial.println("Behavioral trial started");
}

void handleBehavioralStop() {
  if (behavioralTrialIsActive()) {
    behavioralTrialStop();
    Serial.println("Behavioral trial stopped");
  }
}

void handleGridStart(const String& command) {
  if (behavioralTrialIsActive()) {
    Serial.println("Behavioral trial active");
    return;
  }
  if (gridTrialIsActive()) {
    Serial.println("Grid already running");
    return;
  }
  // Optional order argument after "GRIDSTART"; falls back to the order setting.
  int order = gridSettingsOrder();
  String arg = command.substring(9);
  arg.trim();
  if (arg.length() > 0) {
    order = arg.toInt();
  }
  gridTrialStart(order);
  Serial.println("Grid started (order " + String(constrain(order, 1, 4)) + ")");
}

void handleGridStop() {
  if (gridTrialIsActive()) {
    gridTrialStop();
    Serial.println("Grid stopped");
  }
}

}  // namespace

void serialCommandsInit() {
  Serial.begin(kSerialBaud);
  while (!Serial) {
    // wait for the host to open the serial connection
  }
  Serial.println("experimentStimControl ready. BEHAVIORALSTART/BEHAVIORALSTOP for the "
                  "behavioral task, GRIDSTART [order]/GRIDSTOP for the grid task.");
}

void serialCommandsPoll() {
  if (Serial.available() <= 0) {
    return;
  }

  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command == "BEHAVIORALSTART") {
    handleBehavioralStart();
  } else if (command == "BEHAVIORALSTOP") {
    handleBehavioralStop();
  } else if (command == "BEHAVIORALMODE DEFAULT") {
    behavioralSettingsSetMode(BehavioralMode::Default);
    Serial.println("Behavioral mode: default");
  } else if (command == "BEHAVIORALMODE ADVANCED") {
    behavioralSettingsSetMode(BehavioralMode::Advanced);
    Serial.println("Behavioral mode: advanced");
  } else if (command.startsWith("BEHAVIORALSET ")) {
    handleSetCommand(command.substring(14), behavioralSettingsTrySet,
                      behavioralSettingsMode() == BehavioralMode::Advanced);
  } else if (command == "BEHAVIORALGET") {
    printBehavioralSettings();
  } else if (command == "GRIDSTART" || command.startsWith("GRIDSTART ")) {
    handleGridStart(command);
  } else if (command == "GRIDSTOP") {
    handleGridStop();
  } else if (command == "GRIDMODE DEFAULT") {
    gridSettingsSetMode(GridMode::Default);
    Serial.println("Grid mode: default");
  } else if (command == "GRIDMODE ADVANCED") {
    gridSettingsSetMode(GridMode::Advanced);
    Serial.println("Grid mode: advanced");
  } else if (command.startsWith("GRIDSET ")) {
    handleSetCommand(command.substring(8), gridSettingsTrySet,
                      gridSettingsMode() == GridMode::Advanced);
  } else if (command == "GRIDGET") {
    printGridSettings();
  } else {
    Serial.println("Unknown command");
  }
}
