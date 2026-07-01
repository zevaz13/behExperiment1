#ifndef LED_CONTROL_H
#define LED_CONTROL_H

#include "globals.h"

void ledPinConfig();
void setLed(LedId id, int value);   // set one LED and update ledVal[]
void allLedsOff();                   // zero all LEDs and ledVal[]

#endif
