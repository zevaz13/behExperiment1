#pragma once

#include <Arduino.h>

// Runtime-configurable experiment parameters. In Default mode, values are
// pinned to the config.h constants and SET commands are rejected. In
// Advanced mode, SET commands take effect immediately.
enum class Mode { Default, Advanced };

void settingsInit();
Mode settingsMode();
void settingsSetMode(Mode mode);

// Applies a named setting if currently in Advanced mode. Returns false if
// rejected (wrong mode or unknown name).
bool settingsTrySet(const String& name, long value);

unsigned int settingsFlickerFrequencyHz();
unsigned int settingsAmberValue();
unsigned int settingsMaxRed();
unsigned int settingsMaxGreen();
unsigned int settingsMinRed();
unsigned int settingsMinGreen();
