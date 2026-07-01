#ifndef GRID_MODE_H
#define GRID_MODE_H

// Run Grid mode: sweeps LEDA x LEDB across a steps x steps grid (diagonal
// boustrophedon traversal, gridOrder transform), flickering against reference
// LEDs. Runs baselines before and after. Returns when started=false.
void runGrid();

#endif
