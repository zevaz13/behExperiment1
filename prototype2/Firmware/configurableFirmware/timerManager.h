#ifndef TIMER_MANAGER_H
#define TIMER_MANAGER_H

#include <Arduino.h>

// Flicker timer — period set by mode; each mode provides its own ISR.
void startFlicker(void (*isr)(), unsigned long halfPeriodUs);
void stopFlicker();

// Stream timer — fires serialFrameOutput() every 100 ms; start once in setup().
void startStream();

#endif
