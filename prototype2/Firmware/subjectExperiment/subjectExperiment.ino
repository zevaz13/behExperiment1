#include <Arduino.h>
#include <TeensyThreads.h>

#include "pinDefs.h"
#include "globals.h"
#include "ledControl.h"
#include "behavioralExperiment.h"
#include "gridExperiment.h"

// Experiment thread: idle-waits until started=true, then runs the chosen experiment.
void experimentThread() {
    while (true) {
        if (!started) { threads.yield(); continue; }
        if (expMode == EXP_BEHAVIORAL) {
            runBehavioralExperiment();
        } else {
            runGridExperiment();
        }
        started = false;
    }
}

// Parse "key=value" config commands. Returns true if recognized.
static bool handleConfig(const String& cmd) {
    int eq = cmd.indexOf('=');
    if (eq < 0) return false;

    String key = cmd.substring(0, eq);
    int    val = cmd.substring(eq + 1).toInt();
    key.trim();

    if      (key == "freq")            { freq            = val; updateHalfPeriod(); }
    else if (key == "refAmber")        { refAmber        = val; }
    else if (key == "refCyan")         { refCyan         = val; }
    else if (key == "maxA")            { maxA            = val; }
    else if (key == "minA")            { minA            = val; }
    else if (key == "maxB")            { maxB            = val; }
    else if (key == "minB")            { minB            = val; }
    else if (key == "nBaselinesStart") { nBaselinesStart = val; }
    else if (key == "nBaselinesEnd")   { nBaselinesEnd   = val; }
    else if (key == "trialLength")     { trialLength     = (unsigned int)val; }
    else if (key == "interTrialWait")  { interTrialWait  = (unsigned int)val; }
    else if (key == "order")           { gridOrder       = val; }
    else return false;

    Serial.print("SET ");
    Serial.print(key);
    Serial.print("=");
    Serial.println(val);
    return true;
}

void setup() {
    Serial.begin(38400);
    while (!Serial);

    LedpinConfig();
    pinMode(TRIGGER,    OUTPUT);
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    analogWriteResolution(12);
    analogReadResolution(12);

    // Serial frame output timer — fires every 100 ms, returns immediately when !started
    timerSerial.begin(serialFrameOutput, 100000);

    threads.addThread(experimentThread, 1);

    Serial.println("Ready.");
}

void loop() {
    if (!Serial.available()) return;

    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.length() == 0) return;

    // Batch config: semicolon-separated key=value pairs (e.g. "freq=10;maxA=3200;minA=0")
    if (cmd.indexOf(';') >= 0) {
        int pos = 0;
        while (pos <= (int)cmd.length()) {
            int semi = cmd.indexOf(';', pos);
            String tok = (semi < 0) ? cmd.substring(pos) : cmd.substring(pos, semi);
            tok.trim();
            if (tok.length() > 0 && !handleConfig(tok)) {
                Serial.print("ERR unknown param: ");
                Serial.println(tok);
            }
            if (semi < 0) break;
            pos = semi + 1;
        }
        return;
    }

    // Stop always accepted
    if (cmd.equalsIgnoreCase("stop")) {
        started = false;
        Serial.println("Stopped.");
        return;
    }

    // Get returns all current configurable parameter values
    if (cmd.equalsIgnoreCase("get")) {
        Serial.print("freq=");            Serial.println(freq);
        Serial.print("refAmber=");        Serial.println(refAmber);
        Serial.print("refCyan=");         Serial.println(refCyan);
        Serial.print("maxA=");            Serial.println(maxA);
        Serial.print("minA=");            Serial.println(minA);
        Serial.print("maxB=");            Serial.println(maxB);
        Serial.print("minB=");            Serial.println(minB);
        Serial.print("nBaselinesStart="); Serial.println(nBaselinesStart);
        Serial.print("nBaselinesEnd=");   Serial.println(nBaselinesEnd);
        Serial.print("trialLength=");     Serial.println(trialLength);
        Serial.print("interTrialWait=");  Serial.println(interTrialWait);
        Serial.print("order=");           Serial.println(gridOrder);
        Serial.print("mode=");
        Serial.print(expMode == EXP_BEHAVIORAL ? "beh" : "grid");
        Serial.print("-");
        Serial.println(colorPair == PAIR_RG ? "rg" : "bg");
        Serial.println("# use defaults-rg / defaults-bg to restore color-pair defaults");
        return;
    }

    // Config commands accepted anytime
    if (handleConfig(cmd)) return;

    // Mode/start commands only when idle
    if (started) {
        Serial.println("ERR busy");
        return;
    }

    trCnt    = 0;
    trigFlag = 0;

    if (cmd.equalsIgnoreCase("defaults-rg")) {
        applyDefaultsRG();
        Serial.println("DEFAULTS rg applied");
    } else if (cmd.equalsIgnoreCase("defaults-bg")) {
        applyDefaultsBG();
        Serial.println("DEFAULTS bg applied");
    } else if (cmd.equalsIgnoreCase("beh-rg")) {
        colorPair = PAIR_RG; expMode = EXP_BEHAVIORAL;
        started = true;
        Serial.println("START beh-rg");
    } else if (cmd.equalsIgnoreCase("beh-bg")) {
        colorPair = PAIR_BG; expMode = EXP_BEHAVIORAL;
        started = true;
        Serial.println("START beh-bg");
    } else if (cmd.equalsIgnoreCase("grid-rg")) {
        colorPair = PAIR_RG; expMode = EXP_GRID;
        started = true;
        Serial.println("START grid-rg");
    } else if (cmd.equalsIgnoreCase("grid-bg")) {
        colorPair = PAIR_BG; expMode = EXP_GRID;
        started = true;
        Serial.println("START grid-bg");
    } else if (cmd.equalsIgnoreCase("beh-rg-default")) {
        applyDefaultsRG();
        colorPair = PAIR_RG; expMode = EXP_BEHAVIORAL;
        started = true;
        Serial.println("START beh-rg (defaults)");
    } else if (cmd.equalsIgnoreCase("beh-bg-default")) {
        applyDefaultsBG();
        colorPair = PAIR_BG; expMode = EXP_BEHAVIORAL;
        started = true;
        Serial.println("START beh-bg (defaults)");
    } else if (cmd.equalsIgnoreCase("grid-rg-default")) {
        applyDefaultsRG();
        colorPair = PAIR_RG; expMode = EXP_GRID;
        started = true;
        Serial.println("START grid-rg (defaults)");
    } else if (cmd.equalsIgnoreCase("grid-bg-default")) {
        applyDefaultsBG();
        colorPair = PAIR_BG; expMode = EXP_GRID;
        started = true;
        Serial.println("START grid-bg (defaults)");
    } else {
        Serial.print("ERR unknown: ");
        Serial.println(cmd);
    }
}
