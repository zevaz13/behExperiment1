#include "linearMode.h"
#include "globals.h"
#include "pinDefs.h"
#include "ledControl.h"
#include "timerManager.h"

static volatile bool flickerPhase = false;

// Stim phase: LEDA + bgStim1 + bgStim2. Ref phase: ref1 + ref2 + ref3.
static void linearFlickerISR() {
    flickerPhase = !flickerPhase;

    if (!flickerPhase) {
        // Stim phase — all off first, then stim LEDs
        analogWrite(PIN_RED,    0);
        analogWrite(PIN_YELLOW, 0);
        analogWrite(PIN_GREEN,  0);
        analogWrite(PIN_BLUE,   0);
        analogWrite(PIN_CYAN,   0);
        int pinA = ledPin(ledA);
        if (pinA >= 0) analogWrite(pinA, ledVal[ledA]);
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

// Solid baseline LEDs for baseline trials (no flicker).
static void runBaselines(int count, int startCount) {
    for (int i = 0; i < count && started; i++) {
        trCnt = startCount + i;

        // Show baseline LEDs solid — update ledVal[] so the frame reflects them
        for (int j = 0; j < 5; j++) ledVal[j] = 0;
        if (baselineLed1 != LED_NONE) { ledVal[baselineLed1] = baselineLed1Val; analogWrite(ledPin(baselineLed1), baselineLed1Val); }
        if (baselineLed2 != LED_NONE) { ledVal[baselineLed2] = baselineLed2Val; analogWrite(ledPin(baselineLed2), baselineLed2Val); }
        if (baselineLed3 != LED_NONE) { ledVal[baselineLed3] = baselineLed3Val; analogWrite(ledPin(baselineLed3), baselineLed3Val); }

        trigFlag = 1;
        digitalWrite(PIN_TRIGGER, HIGH);

        unsigned long t0 = millis();
        while (millis() - t0 < trialLength && started) {}

        allLedsOff();
        trigFlag = 0;
        digitalWrite(PIN_TRIGGER, LOW);

        delay(interTrialWait);
    }
}

void runLinear() {
    // Build linear step array
    int stimA[50];
    for (int i = 0; i < steps; i++) {
        stimA[i] = (steps == 1) ? minA
                                : minA + (long)i * (maxA - minA) / (steps - 1);
    }

    runBaselines(nBaselinesStart, 1001);

    for (int i = 0; i < steps && started; i++) {
        trCnt = i + 1;

        // Set LEDA value for this step (read by ISR and data frame)
        for (int j = 0; j < 5; j++) ledVal[j] = 0;
        if (ledA != LED_NONE) ledVal[ledA] = stimA[i];

        // Seed true so the first ISR toggle (true -> false) lands on the stim phase.
        flickerPhase = true;
        trigFlag = 1;
        digitalWrite(PIN_TRIGGER, HIGH);
        startFlicker(linearFlickerISR, halfPeriod);

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
