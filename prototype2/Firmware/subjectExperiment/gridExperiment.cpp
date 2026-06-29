#include "gridExperiment.h"
#include "globals.h"
#include "pinDefs.h"
#include "ledControl.h"

static int stimA[NUM_STEPS];
static int stimB[NUM_STEPS];
static int tempCoords[NUM_STIMS][2];
static int expSequence[NUM_STIMS][2];

static void buildArrays() {
    for (int i = 0; i < NUM_STEPS; i++) {
        stimA[i] = minA + (long)i * (maxA - minA) / (NUM_STEPS - 1);
        stimB[i] = minB + (long)i * (maxB - minB) / (NUM_STEPS - 1);
    }
}

// Diagonal coordinates: sum of indices walks 0..2*(NUM_STEPS-1)
static void buildDiagonalCoords() {
    int idx = 0;
    for (int s = 0; s <= 2 * (NUM_STEPS - 1); s++) {
        for (int i = 0; i < NUM_STEPS; i++) {
            int j = s - i;
            if (j >= 0 && j < NUM_STEPS) {
                tempCoords[idx][0] = i;
                tempCoords[idx][1] = j;
                idx++;
            }
        }
    }
}

// Map diagonal coordinates to intensity values, applying order transformation.
// Order 1: (minA, minB) start; Order 2: (minA, maxB); Order 3: (maxA, minB); Order 4: (maxA, maxB)
static void buildExpSequence() {
    buildDiagonalCoords();
    for (int i = 0; i < NUM_STIMS; i++) {
        int a = tempCoords[i][0];
        int b = tempCoords[i][1];
        if (gridOrder == 2 || gridOrder == 4) b = (NUM_STEPS - 1) - b;
        if (gridOrder == 3 || gridOrder == 4) a = (NUM_STEPS - 1) - a;
        expSequence[i][0] = stimA[a];
        expSequence[i][1] = stimB[b];
    }
}

// Baseline: solid reference LEDs (no flicker), then off during ITI.
// startCount sets trCnt for the first baseline in this batch.
// Baselines are numbered 101+ to distinguish them from stimulus trials.
static void runBaselines(int reps, int startCount) {
    currentRed   = 0;
    currentGreen = 0;
    currentBlue  = 0;

    for (int i = 0; i < reps; i++) {
        if (!started) return;

        trCnt        = startCount + i;
        currentAmber = refAmber;
        currentCyan  = refCyan;

        // Solid reference — no flicker timer
        analogWrite(RED,   0);
        analogWrite(BLUE,  0);
        analogWrite(GREEN, 0);
        analogWrite(AMBER, refAmber);
        analogWrite(CYAN,  refCyan);

        trigFlag = 1;
        digitalWrite(TRIGGER, HIGH);

        unsigned long t0 = millis();
        while (millis() - t0 < trialLength) {
            if (!started) return;
        }

        analogWrite(AMBER, 0);
        analogWrite(CYAN,  0);
        currentAmber = 0;
        currentCyan  = 0;
        trigFlag     = 0;
        digitalWrite(TRIGGER, LOW);

        delay(interTrialWait);
    }
}

void runGridExperiment() {
    buildArrays();
    buildExpSequence();

    int baselineCnt = 101;
    runBaselines(nBaselinesStart, baselineCnt);
    baselineCnt += nBaselinesStart;

    for (int i = 0; i < NUM_STIMS; i++) {
        if (!started) break;

        trCnt = i + 1;  // 1-based stimulus trial count

        // Reference values set each trial so flickerISR always has current refAmber/refCyan
        currentAmber = refAmber;
        currentCyan  = refCyan;

        if (colorPair == PAIR_RG) {
            currentRed  = expSequence[i][0];
            currentBlue = 0;
        } else {
            currentBlue = expSequence[i][0];
            currentRed  = 0;
        }
        currentGreen = expSequence[i][1];

        trigFlag = 1;
        digitalWrite(TRIGGER, HIGH);
        startFlicker();

        unsigned long t0 = millis();
        while (millis() - t0 < trialLength) {
            if (!started) break;
        }

        stopFlicker();
        trigFlag = 0;
        digitalWrite(TRIGGER, LOW);
        currentRed = currentGreen = currentBlue = currentAmber = currentCyan = 0;

        delay(interTrialWait);
    }

    if (started) runBaselines(nBaselinesEnd, baselineCnt);

    started  = false;
    trigFlag = 0;
    currentRed = currentGreen = currentBlue = currentAmber = currentCyan = 0;
    Serial.println("DONE");
}
