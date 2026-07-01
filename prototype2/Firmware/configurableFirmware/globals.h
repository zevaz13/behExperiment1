#ifndef GLOBALS_H
#define GLOBALS_H

#include <Arduino.h>
#include <IntervalTimer.h>

// ── State machine ──────────────────────────────────────────────────────────
enum FwState { STATE_IDLE, STATE_CONFIGURED, STATE_RUNNING };
enum Mode    { MODE_NONE = 0, MODE_SOLID, MODE_LINEAR, MODE_GRID, MODE_BEHAVIORAL };

// LED identity — index also used into ledVal[]
enum LedId   { LED_RED = 0, LED_YELLOW, LED_GREEN, LED_BLUE, LED_CYAN, LED_NONE };

extern FwState fwState;
extern Mode    activeMode;

// ── Timing parameters ─────────────────────────────────────────────────────
extern int          freq;
extern unsigned int trialLength;
extern unsigned int interTrialWait;
extern int          nBaselinesStart;
extern int          nBaselinesEnd;
extern int          steps;       // linear/grid step count [2, 50]
extern int          gridOrder;   // grid traversal order [0, 4]
extern volatile unsigned long halfPeriod;  // µs, derived from freq

// ── LED assignments ────────────────────────────────────────────────────────
extern LedId ledA;           // primary flickering LED (Linear/Grid/Behavioral)
extern LedId ledB;           // secondary flickering LED (Grid/Behavioral)
extern int   maxA, minA;
extern int   maxB, minB;

extern LedId bgStim1Led;     // background LED during stim phase
extern int   bgStim1Int;
extern LedId bgStim2Led;
extern int   bgStim2Int;

extern LedId ref1Led, ref2Led, ref3Led;  // reference phase LEDs
extern int   ref1Int, ref2Int, ref3Int;

extern LedId baselineLed1, baselineLed2, baselineLed3;  // baseline solid-display LEDs
extern int   baselineLed1Val, baselineLed2Val, baselineLed3Val;

// ── Hue sensor ────────────────────────────────────────────────────────────
extern bool hueEnabled;
extern volatile int hueR, hueG, hueB, hueCT, hueL;

// ── Live LED output values ─────────────────────────────────────────────────
// Index by LedId; written by mode code and flickerISR, read by dataFrame.
extern volatile int ledVal[5];

// ── Frame / experiment state ───────────────────────────────────────────────
extern volatile bool started;
extern volatile int  trCnt;
extern volatile int  trigFlag;
extern volatile bool pressFlag;  // cleared after each frame that includes it

// ── Hardware timers ───────────────────────────────────────────────────────
extern IntervalTimer timerFlicker;
extern IntervalTimer timerSerial;

// ── Helpers ───────────────────────────────────────────────────────────────
void updateHalfPeriod();
void applyDefaults();
int  ledPin(LedId id);
const char* ledIdStr(LedId id);
LedId parseLedId(const String& s);
bool  isValidLedName(const String& s);

#endif
