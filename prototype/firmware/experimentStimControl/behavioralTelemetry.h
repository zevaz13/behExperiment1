#pragma once

// Streams live trial data (red/green/amber) over serial every 100 ms while a
// behavioral trial is active, so a GUI can plot it in real time.
void behavioralTelemetryInit();
void behavioralTelemetryPoll();
