#include "dataFrame.h"
#include "globals.h"

void serialFrameOutput() {
    if (!started) return;

    Serial.print("FRAME@");
    Serial.print(trCnt);          Serial.print("@");
    Serial.print(ledVal[LED_RED]);    Serial.print("@");
    Serial.print(ledVal[LED_YELLOW]); Serial.print("@");
    Serial.print(ledVal[LED_GREEN]);  Serial.print("@");
    Serial.print(ledVal[LED_BLUE]);   Serial.print("@");
    Serial.print(ledVal[LED_CYAN]);   Serial.print("@");
    Serial.print(hueEnabled ? hueR  : -99); Serial.print("@");
    Serial.print(hueEnabled ? hueG  : -99); Serial.print("@");
    Serial.print(hueEnabled ? hueB  : -99); Serial.print("@");
    Serial.print(hueEnabled ? hueCT : -99); Serial.print("@");
    Serial.print(hueEnabled ? hueL  : -99); Serial.print("@");
    Serial.print(ledIdStr(ledA));   Serial.print("@");
    Serial.print(ledIdStr(ledB));   Serial.print("@");
    Serial.print(pressFlag ? 1 : 0); Serial.print("@");
    Serial.println(trigFlag);

    pressFlag = false;
}
