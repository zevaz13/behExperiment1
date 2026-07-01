#include "baselineRunner.h"
#include "globals.h"
#include "pinDefs.h"
#include "ledControl.h"

void runBaselines(int count, int startCount) {
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
