#include <Arduino.h>
#include <Wire.h>
#include <TeensyThreads.h>

#include "pinDefs.h"
#include "globals.h"
#include "ledControl.h"
#include "timerManager.h"
#include "serialParser.h"
#include "dataFrame.h"
#include "hueSensor.h"

#include "solidMode.h"
#include "linearMode.h"
// #include "gridMode.h"      // M5
// #include "behavioralMode.h" // M6

// Experiment thread: waits for started=true, dispatches to mode, then resets.
void experimentThread() {
    while (true) {
        if (!started) { threads.yield(); continue; }

        switch (activeMode) {
            case MODE_SOLID:      runSolid();      break;
            case MODE_LINEAR:     runLinear();     break;
            // case MODE_GRID:       runGrid();       break;  // M5
            // case MODE_BEHAVIORAL: runBehavioral(); break;  // M6
            default:
                while (started) { threads.yield(); }
                break;
        }

        started    = false;
        fwState    = STATE_IDLE;
        activeMode = MODE_NONE;
        allLedsOff();
        trigFlag = 0;
        digitalWrite(PIN_TRIGGER, LOW);
    }
}

void setup() {
    Serial.begin(38400);
    while (!Serial);

    ledPinConfig();
    pinMode(PIN_TRIGGER, OUTPUT);
    pinMode(PIN_BUTTON,  INPUT_PULLUP);
    analogWriteResolution(12);
    analogReadResolution(12);

    startStream();
    threads.addThread(experimentThread, 1);

    Serial.println("Ready.");
}

void loop() {
    if (hueEnabled) readHue();
    handleSerial();
}
