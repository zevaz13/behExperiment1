#include "solidMode.h"
#include "globals.h"
#include "pinDefs.h"
#include <Bounce.h>

void runSolid() {
    // Apply LED values that may have been SET before START
    for (int i = 0; i < 5; i++) {
        int pin = ledPin((LedId)i);
        if (pin >= 0) analogWrite(pin, ledVal[i]);
    }

    Bounce btn(PIN_BUTTON, 25);
    while (started) {
        btn.update();
        if (btn.fallingEdge()) {
            trCnt++;
            pressFlag = true;
        }
        delayMicroseconds(1000);
    }
    // allLedsOff() and state reset handled by experimentThread
}
