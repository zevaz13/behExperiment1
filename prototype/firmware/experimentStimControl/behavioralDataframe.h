#pragma once

// Sends one log line over serial, matching the GUI's log header:
// TriggerCue TrialNumber Amber red green Press.
// TriggerCue is unused in this experiment and always sent as 0.
void behavioralSendDataFrame(int amberValue, int redValue, int greenValue, int press, int trialNumber);
