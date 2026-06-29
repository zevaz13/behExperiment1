#ifndef LED_CONTROL_H
#define LED_CONTROL_H

#include <Arduino.h>

void LedpinConfig();
void flickerISR();
void startFlicker();
void stopFlicker();
void serialFrameOutput();

#endif
