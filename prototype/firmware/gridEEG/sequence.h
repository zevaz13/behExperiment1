#pragma once

// Builds the grid stimulus sequence: kNumStims (= kNumSteps^2) red/green
// combinations, linearly spaced over [minRed,maxRed] / [minGreen,maxGreen],
// visited in a diagonal traversal whose start corner is set by `order`:
//   1 -> (minRed, minGreen)   2 -> (minRed, maxGreen)
//   3 -> (maxRed, minGreen)   4 -> (maxRed, maxGreen)
// Call sequenceBuild() once before reading entries.
void sequenceBuild(int order, int minRed, int maxRed, int minGreen, int maxGreen);

int sequenceCount();
int sequenceRed(int index);
int sequenceGreen(int index);
