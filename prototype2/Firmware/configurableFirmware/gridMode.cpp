#include "gridMode.h"
#include "globals.h"
#include "pinDefs.h"
#include "ledControl.h"
#include "timerManager.h"
#include "baselineRunner.h"

#define MAX_STEPS 50
#define MAX_STIMS (MAX_STEPS * MAX_STEPS)

static volatile bool flickerPhase = false;

// Stim phase: LEDA + LEDB + bgStim1 + bgStim2. Ref phase: ref1 + ref2 + ref3.
static void gridFlickerISR() {
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

static int seqA[MAX_STIMS], seqB[MAX_STIMS];

// Diagonal (boustrophedon) traversal of the steps x steps grid: each diagonal
// s = i + j is walked in alternating direction so consecutive stimuli stay
// adjacent, rather than jumping back across the grid each diagonal. Matches
// subjectExperiment/gridExperiment.cpp buildDiagonalCoords/buildExpSequence.
// Order 2/4 flip the B axis, order 3/4 flip the A axis; order 0 and 1 are
// both the identity (start at minA, minB).
static void buildSequence() {
    int stimA[MAX_STEPS], stimB[MAX_STEPS];
    for (int i = 0; i < steps; i++) {
        stimA[i] = (steps == 1) ? minA : minA + (long)i * (maxA - minA) / (steps - 1);
        stimB[i] = (steps == 1) ? minB : minB + (long)i * (maxB - minB) / (steps - 1);
    }

    int idx = 0;
    for (int s = 0; s <= 2 * (steps - 1); s++) {
        int iLo = max(0, s - (steps - 1));
        int iHi = min(s, steps - 1);
        if (s % 2 == 0) {
            for (int i = iHi; i >= iLo; i--) {
                int a = i, b = s - i;
                if (gridOrder == 2 || gridOrder == 4) b = (steps - 1) - b;
                if (gridOrder == 3 || gridOrder == 4) a = (steps - 1) - a;
                seqA[idx] = stimA[a];
                seqB[idx] = stimB[b];
                idx++;
            }
        } else {
            for (int i = iLo; i <= iHi; i++) {
                int a = i, b = s - i;
                if (gridOrder == 2 || gridOrder == 4) b = (steps - 1) - b;
                if (gridOrder == 3 || gridOrder == 4) a = (steps - 1) - a;
                seqA[idx] = stimA[a];
                seqB[idx] = stimB[b];
                idx++;
            }
        }
    }
}

void runGrid() {
    buildSequence();
    int totalStims = steps * steps;

    runBaselines(nBaselinesStart, 1001);

    for (int i = 0; i < totalStims && started; i++) {
        trCnt = i + 1;

        // Set LEDA/LEDB values for this grid point (read by ISR and data frame)
        for (int j = 0; j < 5; j++) ledVal[j] = 0;
        if (ledA != LED_NONE) ledVal[ledA] = seqA[i];
        if (ledB != LED_NONE) ledVal[ledB] = seqB[i];

        // Seed true so the first ISR toggle (true -> false) lands on the stim phase.
        flickerPhase = true;
        trigFlag = 1;
        digitalWrite(PIN_TRIGGER, HIGH);
        startFlicker(gridFlickerISR, halfPeriod);

        unsigned long t0 = millis();
        while (millis() - t0 < trialLength && started) {}

        stopFlicker();
        trigFlag = 0;
        digitalWrite(PIN_TRIGGER, LOW);
        allLedsOff();

        delay(interTrialWait);
    }

    if (started) runBaselines(nBaselinesEnd, 1001 + nBaselinesStart);
}
