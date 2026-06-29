#include "globals.h"

ColorPair colorPair = PAIR_RG;
ExpMode   expMode   = EXP_BEHAVIORAL;

// Configurable parameters — RG behavioral defaults
int          freq            = 10;
int          refAmber        = 2400;
int          refCyan         = 0;
int          maxA            = 3200;
int          minA            = 0;
int          maxB            = 2000;
int          minB            = 0;
int          nBaselinesStart = 2;
int          nBaselinesEnd   = 2;
unsigned int trialLength     = 3000;
unsigned int interTrialWait  = 750;
int          gridOrder       = 1;

volatile unsigned long halfPeriod = 50000;  // 10 Hz → 50 ms half-period in µs

volatile int currentRed   = 0;
volatile int currentGreen = 0;
volatile int currentBlue  = 0;
volatile int currentAmber = 0;
volatile int currentCyan  = 0;

volatile bool started  = false;
volatile int  trCnt    = 0;
volatile int  trigFlag = 0;

IntervalTimer timerFlicker;
IntervalTimer timerSerial;

void updateHalfPeriod() {
    halfPeriod = 1000000UL / (2 * (unsigned long)freq);
}

void applyDefaultsRG() {
    freq = 10; refAmber = 2400; refCyan = 0;
    minA = 0; maxA = 3200; minB = 0; maxB = 2000;
    nBaselinesStart = 2; nBaselinesEnd = 2;
    trialLength = 3000; interTrialWait = 750;
    updateHalfPeriod();
}

void applyDefaultsBG() {
    freq = 10; refAmber = 500; refCyan = 1400;
    minA = 0; maxA = 2800; minB = 0; maxB = 2000;
    nBaselinesStart = 2; nBaselinesEnd = 2;
    trialLength = 3000; interTrialWait = 750;
    updateHalfPeriod();
}
