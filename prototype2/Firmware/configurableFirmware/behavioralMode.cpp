#include "behavioralMode.h"
#include "globals.h"
#include "pinDefs.h"
#include "ledControl.h"
#include "timerManager.h"
#include "dataFrame.h"
#include <Bounce.h>

static volatile bool flickerPhase = false;

// Stim phase: LEDA + LEDB (live knob values) + bgStim1 + bgStim2. Ref phase: ref1 + ref2 + ref3.
static void behavioralFlickerISR() {
    flickerPhase = !flickerPhase;

    if (!flickerPhase) {
        // Stim phase — all off first, then stim LEDs
        analogWrite(PIN_RED,    0);
        analogWrite(PIN_YELLOW, 0);
        analogWrite(PIN_GREEN,  0);
        analogWrite(PIN_BLUE,   0);
        analogWrite(PIN_CYAN,   0);
        int pinA = ledPin(ledA); if (pinA >= 0) analogWrite(pinA, ledVal[ledA]);
        int pinB = ledPin(ledB); if (pinB >= 0) analogWrite(pinB, ledVal[ledB]);
        int p1 = ledPin(bgStim1Led); if (p1 >= 0) analogWrite(p1, bgStim1Int);
        int p2 = ledPin(bgStim2Led); if (p2 >= 0) analogWrite(p2, bgStim2Int);
    } else {
        // Ref phase — all off first, then ref LEDs
        analogWrite(PIN_RED,    0);
        analogWrite(PIN_YELLOW, 0);
        analogWrite(PIN_GREEN,  0);
        analogWrite(PIN_BLUE,   0);
        analogWrite(PIN_CYAN,   0);
        int r1 = ledPin(ref1Led); if (r1 >= 0) analogWrite(r1, ref1Int);
        int r2 = ledPin(ref2Led); if (r2 >= 0) analogWrite(r2, ref2Int);
        int r3 = ledPin(ref3Led); if (r3 >= 0) analogWrite(r3, ref3Int);
    }
}

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

// Anchor-offset knob strategy and trial walk mirror
// subjectExperiment/behavioralExperiment.cpp, generalized to configurable LEDA/LEDB.
// Each trial: anchor knobs to target -> flicker -> read knobs live -> button press
// (physical or serial PRESS) -> ITI -> walk to a new random target -> repeat.
// First trial starts at the interior margin (1/5 of range from min). No baselines,
// no hue, no fixed trial count or trialLength — runs until STOP.
void runBehavioral() {
    Bounce btn(PIN_BUTTON, 25);

    int targetA = minA + (maxA - minA) / 5;
    int targetB = minB + (maxB - minB) / 5;

    while (started) {
        // Anchor: compute ADC offsets so the current physical knob position reads as targetA/targetB
        int offsetA = (ledA != LED_NONE) ? rawFromMapped(targetA, minA, maxA) - analogRead(PIN_KNOB_A) : 0;
        int offsetB = (ledB != LED_NONE) ? rawFromMapped(targetB, minB, maxB) - analogRead(PIN_KNOB_B) : 0;

        trCnt++;
        trigFlag = 1;
        digitalWrite(PIN_TRIGGER, HIGH);
        flickerPhase = true;  // seed so the first ISR toggle lands on the stim phase
        startFlicker(behavioralFlickerISR, halfPeriod);

        int pressA = 0, pressB = 0;

        // Trial loop: update LED values from anchored knob readings until button pressed
        while (started) {
            if (ledA != LED_NONE) ledVal[ledA] = constrain(map(wrapAdc(analogRead(PIN_KNOB_A) + offsetA), 0, 4095, minA, maxA), minA, maxA);
            if (ledB != LED_NONE) ledVal[ledB] = constrain(map(wrapAdc(analogRead(PIN_KNOB_B) + offsetB), 0, 4095, minB, maxB), minB, maxB);

            btn.update();
            bool pressed = btn.fallingEdge() || guiPressRequest;

            if (pressed) {
                guiPressRequest = false;
                pressA = (ledA != LED_NONE) ? ledVal[ledA] : 0;
                pressB = (ledB != LED_NONE) ? ledVal[ledB] : 0;
                pressFlag = true;

                stopFlicker();
                trigFlag = 0;
                digitalWrite(PIN_TRIGGER, LOW);
                // Force out the press-event frame now, while ledVal[] still holds the
                // pressed intensities — the periodic 100ms FRAME timer is async and
                // would otherwise almost always fire after allLedsOff() below zeroes
                // them, reporting 0/0 instead of the actual pressed values.
                serialFrameOutput();
                allLedsOff();

                delay(interTrialWait);

                int marginA = (maxA - minA) / 5;
                int marginB = (maxB - minB) / 5;
                targetA = constrain(pressA + walkJump(minA, maxA), minA + marginA, maxA - marginA);
                targetB = constrain(pressB + walkJump(minB, maxB), minB + marginB, maxB - marginB);
                break;
            }

            if (!started) break;
            delayMicroseconds(1000);
        }
    }

    stopFlicker();
    trigFlag = 0;
    digitalWrite(PIN_TRIGGER, LOW);
    allLedsOff();
}
