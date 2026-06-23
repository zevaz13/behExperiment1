#pragma once

#include <Arduino.h>

// Runtime-configurable grid experiment parameters. In Default mode, values
// are pinned to the gridConfig.h constants and GRIDSET is rejected. In
// Advanced mode, GRIDSET takes effect immediately.
enum class GridMode { Default, Advanced };

void gridSettingsInit();
GridMode gridSettingsMode();
void gridSettingsSetMode(GridMode mode);

// Applies a named setting if currently in Advanced mode. Returns false if
// rejected (wrong mode or unknown name).
bool gridSettingsTrySet(const String& name, long value);

unsigned int gridSettingsFlickerFrequencyHz();
unsigned int gridSettingsAmberValue();
unsigned int gridSettingsMinRed();
unsigned int gridSettingsMaxRed();
unsigned int gridSettingsMinGreen();
unsigned int gridSettingsMaxGreen();
unsigned int gridSettingsTrialLengthMs();
unsigned int gridSettingsInterTrialWaitMs();
unsigned int gridSettingsBaselinesStart();
unsigned int gridSettingsBaselinesEnd();
unsigned int gridSettingsOrder();
