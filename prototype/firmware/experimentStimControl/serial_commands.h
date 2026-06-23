#pragma once

// Reads control commands for both experiments from Serial and dispatches
// them. See docs/experimentStimControl-configure.md for the full command set.
void serialCommandsInit();
void serialCommandsPoll();
