#include "ledControl.h"
#include "globals.h"
#include "pinDefs.h"

static volatile bool flickerPhase = false;

void LedpinConfig() {
    pinMode(AMBER, OUTPUT);
    pinMode(RED,   OUTPUT);
    pinMode(BLUE,  OUTPUT);
    pinMode(GREEN, OUTPUT);
    pinMode(CYAN,  OUTPUT);
    analogWrite(AMBER, 0);
    analogWrite(RED,   0);
    analogWrite(BLUE,  0);
    analogWrite(GREEN, 0);
    analogWrite(CYAN,  0);
}

// Single ISR: Phase A = stimulus ON, reference OFF; Phase B = stimulus OFF, reference ON.
// No dark gap between phases — direct toggle each half-period.
void flickerISR() {
    flickerPhase = !flickerPhase;

    if (!flickerPhase) {
        // Phase A: stimulus LEDs on
        if (colorPair == PAIR_RG) {
            analogWrite(RED,  currentRed);
            analogWrite(BLUE, 0);
        } else {
            analogWrite(BLUE, currentBlue);
            analogWrite(RED,  0);
        }
        analogWrite(GREEN, currentGreen);
        analogWrite(AMBER, 0);
        analogWrite(CYAN,  0);
    } else {
        // Phase B: reference LEDs on
        analogWrite(RED,   0);
        analogWrite(BLUE,  0);
        analogWrite(GREEN, 0);
        analogWrite(AMBER, currentAmber);
        analogWrite(CYAN,  currentCyan);
    }
}

void startFlicker() {
    flickerPhase = false;
    timerFlicker.begin(flickerISR, halfPeriod);
}

void stopFlicker() {
    timerFlicker.end();
    analogWrite(RED,   0);
    analogWrite(BLUE,  0);
    analogWrite(GREEN, 0);
    analogWrite(AMBER, 0);
    analogWrite(CYAN,  0);
}

// Fired by timerSerial every 100 ms; returns immediately when not running.
void serialFrameOutput() {
    if (!started) return;

    Serial.print("&@STIM:");
    Serial.print(trCnt);
    Serial.print(",Mode:");
    Serial.print(colorPair == PAIR_RG ? "RG" : "BG");
    Serial.print(",RED:");
    Serial.print(currentRed);
    Serial.print(",GREEN:");
    Serial.print(currentGreen);
    Serial.print(",BLUE:");
    Serial.print(currentBlue);
    Serial.print(",AMBER:");
    Serial.print(currentAmber);
    Serial.print(",CYAN:");
    Serial.print(currentCyan);
    Serial.print(",TRIG:");
    Serial.print(trigFlag);
    Serial.println("%!");
}
