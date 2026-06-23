#pragma once

// Serial log frame, parser-compatible with the behavioral firmware's 6-field
// "@"-separated format, with grid meanings:
//   TriggerCue@StimNumber@Amber@Red@Green@Phase
// TriggerCue is the EEG trigger pin state (1 during a trial, 0 in the gap).
// StimNumber is the grid stimulus index (1..kNumStims), or 0 for a baseline.
// Phase: 0 = baseline, 1 = grid stimulus, 2 = intertrial.
constexpr int kGridPhaseBaseline   = 0;
constexpr int kGridPhaseStimulus   = 1;
constexpr int kGridPhaseIntertrial = 2;

void gridSendDataFrame(int triggerCue, int stimNumber, int amberValue,
                        int redValue, int greenValue, int phase);
