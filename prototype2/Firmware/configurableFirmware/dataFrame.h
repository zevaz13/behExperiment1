#ifndef DATA_FRAME_H
#define DATA_FRAME_H

// ISR called by timerSerial every 100 ms.
// Frame format (@ delimited):
//   FRAME@TrialNumber@Red@Yellow@Green@Blue@Cyan@HUE_R@HUE_G@HUE_B@HUE_CT@HUE_L@LEDA@LEDB@Press@Trigger
//
// FRAME is the line identifier (replaces the placeholder TriggerCue field from the
// requirements draft; kept as a fixed string so the GUI can distinguish data frames
// from other serial output).
// Fields not meaningful in the current mode are sent as -99.
// Press is 1 only on the frame immediately following a button press, then resets.
void serialFrameOutput();

#endif
