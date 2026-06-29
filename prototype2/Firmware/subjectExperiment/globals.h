#ifndef GLOBALS_H
#define GLOBALS_H

#include <Arduino.h>
#include <IntervalTimer.h>

enum ColorPair { PAIR_RG = 0, PAIR_BG = 1 };
enum ExpMode   { EXP_BEHAVIORAL = 0, EXP_GRID = 1 };

extern ColorPair colorPair;
extern ExpMode   expMode;

// Configurable parameters (settable via serial commands)
extern int          freq;
extern int          refAmber;
extern int          refCyan;
extern int          maxA, minA;  // primary LED: Red (RG) or Blue (BG)
extern int          maxB, minB;  // secondary LED: Green
extern int          nBaselinesStart;
extern int          nBaselinesEnd;
extern unsigned int trialLength;
extern unsigned int interTrialWait;
extern int          gridOrder;

// Derived timing
extern volatile unsigned long halfPeriod;  // microseconds

// Live LED output values (written by experiment thread, read by flickerISR)
extern volatile int currentRed;
extern volatile int currentGreen;
extern volatile int currentBlue;
extern volatile int currentAmber;
extern volatile int currentCyan;

// Experiment state
extern volatile bool started;
extern volatile int  trCnt;
extern volatile int  trigFlag;

// Hardware timers
extern IntervalTimer timerFlicker;
extern IntervalTimer timerSerial;

void updateHalfPeriod();
void applyDefaultsRG();
void applyDefaultsBG();

#endif
