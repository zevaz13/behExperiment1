#ifndef LINEAR_MODE_H
#define LINEAR_MODE_H

// Run Linear mode: sweeps LEDA across `steps` values from minA to maxA,
// flickering against reference LEDs. Runs baselines before and after.
// Returns when started=false.
void runLinear();

#endif
