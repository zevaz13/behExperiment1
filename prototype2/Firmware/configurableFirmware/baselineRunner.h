#ifndef BASELINE_RUNNER_H
#define BASELINE_RUNNER_H

// Solid baseline display: drives baselineLed1/2/3 at their configured values
// for `count` trials of `trialLength`, trCnt starting at `startCount`.
// Shared by Linear, Grid, and (later) Behavioral modes.
void runBaselines(int count, int startCount);

#endif
