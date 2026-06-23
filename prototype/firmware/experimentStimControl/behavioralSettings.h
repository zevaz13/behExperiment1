#pragma once

#include <Arduino.h>

// Runtime-configurable behavioral experiment parameters. In Default mode,
// values are pinned to the behavioralConfig.h constants and BEHAVIORALSET is
// rejected. In Advanced mode, BEHAVIORALSET takes effect immediately.
enum class BehavioralMode { Default, Advanced };

void behavioralSettingsInit();
BehavioralMode behavioralSettingsMode();
void behavioralSettingsSetMode(BehavioralMode mode);

// Applies a named setting if currently in Advanced mode. Returns false if
// rejected (wrong mode or unknown name).
bool behavioralSettingsTrySet(const String& name, long value);

unsigned int behavioralSettingsFlickerFrequencyHz();
unsigned int behavioralSettingsAmberValue();
unsigned int behavioralSettingsMaxRed();
unsigned int behavioralSettingsMaxGreen();
unsigned int behavioralSettingsMinRed();
unsigned int behavioralSettingsMinGreen();
