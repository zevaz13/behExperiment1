#pragma once

// Sends one log line over serial, matching the GUI's log header:
// TriggerCue TrialNumber Amber red green Press.
// TriggerCue/TrialNumber are unused in this experiment and always sent as 0.
void sendDataFrame(int amberValue, int redValue, int greenValue, int press);
