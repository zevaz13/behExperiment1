#include "globals.h"
#include "pinDefs.h"

FwState fwState   = STATE_IDLE;
Mode    activeMode = MODE_NONE;

int          freq            = 10;
unsigned int trialLength     = 3000;
unsigned int interTrialWait  = 750;
int          nBaselinesStart = 0;
int          nBaselinesEnd   = 0;
int          steps           = 10;
int          gridOrder       = 1;

volatile unsigned long halfPeriod = 50000;  // 10 Hz → 50 ms half-period in µs

LedId ledA = LED_NONE;
LedId ledB = LED_NONE;
int   maxA = 3200, minA = 0;
int   maxB = 2000, minB = 0;

LedId bgStim1Led = LED_NONE;
int   bgStim1Int = 0;
LedId bgStim2Led = LED_NONE;
int   bgStim2Int = 0;

LedId ref1Led = LED_NONE, ref2Led = LED_NONE, ref3Led = LED_NONE;
int   ref1Int = 0, ref2Int = 0, ref3Int = 0;

LedId baselineLed1 = LED_NONE, baselineLed2 = LED_NONE, baselineLed3 = LED_NONE;
int   baselineLed1Val = 0, baselineLed2Val = 0, baselineLed3Val = 0;

bool hueEnabled = false;
volatile int hueR = -99, hueG = -99, hueB = -99, hueCT = -99, hueL = -99;

volatile int  ledVal[5]  = {0, 0, 0, 0, 0};
volatile bool started    = false;
volatile int  trCnt      = 0;
volatile int  trigFlag   = 0;
volatile bool pressFlag  = false;
volatile bool guiPressRequest = false;

IntervalTimer timerFlicker;
IntervalTimer timerSerial;

void updateHalfPeriod() {
    halfPeriod = 1000000UL / (2 * (unsigned long)freq);
}

void applyDefaults() {
    freq = 10; trialLength = 3000; interTrialWait = 750;
    nBaselinesStart = 0; nBaselinesEnd = 0;
    steps = 10; gridOrder = 1;
    maxA = 3200; minA = 0;
    maxB = 2000; minB = 0;
    ledA = LED_NONE; ledB = LED_NONE;
    bgStim1Led = LED_NONE; bgStim1Int = 0;
    bgStim2Led = LED_NONE; bgStim2Int = 0;
    ref1Led = LED_NONE; ref1Int = 0;
    ref2Led = LED_NONE; ref2Int = 0;
    ref3Led = LED_NONE; ref3Int = 0;
    baselineLed1 = LED_NONE; baselineLed1Val = 0;
    baselineLed2 = LED_NONE; baselineLed2Val = 0;
    baselineLed3 = LED_NONE; baselineLed3Val = 0;
    hueEnabled = false;
    guiPressRequest = false;
    updateHalfPeriod();
}

int ledPin(LedId id) {
    switch (id) {
        case LED_RED:    return PIN_RED;
        case LED_YELLOW: return PIN_YELLOW;
        case LED_GREEN:  return PIN_GREEN;
        case LED_BLUE:   return PIN_BLUE;
        case LED_CYAN:   return PIN_CYAN;
        default:         return -1;
    }
}

const char* ledIdStr(LedId id) {
    switch (id) {
        case LED_RED:    return "RED";
        case LED_YELLOW: return "YELLOW";
        case LED_GREEN:  return "GREEN";
        case LED_BLUE:   return "BLUE";
        case LED_CYAN:   return "CYAN";
        default:         return "NONE";
    }
}

LedId parseLedId(const String& s) {
    if (s.equalsIgnoreCase("RED"))    return LED_RED;
    if (s.equalsIgnoreCase("YELLOW")) return LED_YELLOW;
    if (s.equalsIgnoreCase("GREEN"))  return LED_GREEN;
    if (s.equalsIgnoreCase("BLUE"))   return LED_BLUE;
    if (s.equalsIgnoreCase("CYAN"))   return LED_CYAN;
    return LED_NONE;
}

bool isValidLedName(const String& s) {
    return s.equalsIgnoreCase("RED")    || s.equalsIgnoreCase("YELLOW") ||
           s.equalsIgnoreCase("GREEN")  || s.equalsIgnoreCase("BLUE")   ||
           s.equalsIgnoreCase("CYAN")   || s.equalsIgnoreCase("NONE");
}

// True if `val` (a real LED, not NONE) is already assigned to one of the
// other roles in the same phase group — used to reject same-LED-twice SETs.
bool ledInUse(LedId val, LedId s1, LedId s2, LedId s3) {
    if (val == LED_NONE) return false;
    return val == s1 || val == s2 || val == s3;
}
