#include "behavioralExperiment.h"
#include "globals.h"
#include "pinDefs.h"
#include "ledControl.h"
#include <Bounce.h>

// Teensy-bundled Bounce requires (pin, interval_ms) constructor; no default ctor or .attach()
static Bounce btn(BUTTON_PIN, 25);

// Inverse of map(raw, 0, 4095, lo, hi) — gives the raw ADC reading that maps to val.
static int rawFromMapped(int val, int lo, int hi) {
    if (hi <= lo) return 0;
    long raw = (long)(val - lo) * 4095 / (hi - lo);
    return (int)constrain(raw, 0, 4095);
}

// True modulo wrap into [0, 4095] — handles negative values from offset arithmetic.
static int wrapAdc(int v) {
    v %= 4096;
    return v < 0 ? v + 4096 : v;
}

// Fixed jump of range/3 with random sign — guarantees a meaningful move each trial.
static int walkJump(int lo, int hi) {
    int mag = (hi - lo) / 3;
    if (mag <= 0) return 0;
    return (random(0, 2) == 0) ? mag : -mag;
}

// Run continuously until started = false (set by serial "stop" command).
// Each trial: anchor knobs to target → flicker → read knobs → button press → ITI → repeat.
// First trial starts at the interior margin (1/5 of range from min). Subsequent trials walk
// from the previous press position by a random jump — matching prototype1 knob strategy.
void runBehavioralExperiment() {
    currentAmber = refAmber;
    currentCyan  = refCyan;

    // First trial anchors to the interior margin (not at an extreme)
    int targetA = minA + (maxA - minA) / 5;
    int targetB = minB + (maxB - minB) / 5;

    while (started) {
        // Anchor: compute ADC offsets so the current physical knob position reads as targetA/targetB
        int offsetA = rawFromMapped(targetA, minA, maxA) - analogRead(AIred);
        int offsetB = rawFromMapped(targetB, minB, maxB) - analogRead(AIgreen);

        trCnt++;
        trigFlag = 1;
        digitalWrite(TRIGGER, HIGH);
        startFlicker();

        // Trial loop: update LED values from anchored knob readings until button pressed
        while (started) {
            int valA = constrain(map(wrapAdc(analogRead(AIred)   + offsetA), 0, 4095, minA, maxA), minA, maxA);
            int valB = constrain(map(wrapAdc(analogRead(AIgreen) + offsetB), 0, 4095, minB, maxB), minB, maxB);

            if (colorPair == PAIR_RG) {
                currentRed  = valA;
                currentBlue = 0;
            } else {
                currentBlue = valA;
                currentRed  = 0;
            }
            currentGreen = valB;

            btn.update();
            if (btn.fallingEdge()) {
                int pressA = (colorPair == PAIR_RG) ? currentRed : currentBlue;
                int pressB = currentGreen;

                // Log trial response (already-mapped LED output values, not raw ADC)
                Serial.print("RESP,Trial:");
                Serial.print(trCnt);
                Serial.print(",A:");
                Serial.print(pressA);
                Serial.print(",B:");
                Serial.println(pressB);

                stopFlicker();
                trigFlag = 0;
                digitalWrite(TRIGGER, LOW);
                currentRed = currentGreen = currentBlue = 0;

                delay(interTrialWait);

                // Next trial: walk from press position, clamped to interior margin
                int marginA = (maxA - minA) / 5;
                int marginB = (maxB - minB) / 5;
                targetA = constrain(pressA + walkJump(minA, maxA), minA + marginA, maxA - marginA);
                targetB = constrain(pressB + walkJump(minB, maxB), minB + marginB, maxB - marginB);

                break;
            }

            delayMicroseconds(1000);
        }
    }

    // Clean up on stop
    stopFlicker();
    trigFlag = 0;
    digitalWrite(TRIGGER, LOW);
    currentRed = currentGreen = currentBlue = currentAmber = currentCyan = 0;
    Serial.println("DONE");
}
