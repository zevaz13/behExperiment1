#include "ledControl.h"
#include "pinDefs.h"

void ledPinConfig() {
    pinMode(PIN_YELLOW, OUTPUT);
    pinMode(PIN_RED,    OUTPUT);
    pinMode(PIN_BLUE,   OUTPUT);
    pinMode(PIN_GREEN,  OUTPUT);
    pinMode(PIN_CYAN,   OUTPUT);
    allLedsOff();
}

void setLed(LedId id, int value) {
    if (id == LED_NONE) return;
    int pin = ledPin(id);
    ledVal[id] = value;
    analogWrite(pin, value);
}

void allLedsOff() {
    for (int i = 0; i < 5; i++) ledVal[i] = 0;
    analogWrite(PIN_YELLOW, 0);
    analogWrite(PIN_RED,    0);
    analogWrite(PIN_BLUE,   0);
    analogWrite(PIN_GREEN,  0);
    analogWrite(PIN_CYAN,   0);
}
