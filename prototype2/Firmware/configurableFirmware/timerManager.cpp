#include "timerManager.h"
#include "globals.h"
#include "dataFrame.h"

void startFlicker(void (*isr)(), unsigned long halfPeriodUs) {
    timerFlicker.begin(isr, halfPeriodUs);
}

void stopFlicker() {
    timerFlicker.end();
}

void startStream() {
    timerSerial.begin(serialFrameOutput, 100000);  // 100 ms
}
