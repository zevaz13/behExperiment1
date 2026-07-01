#include "serialParser.h"
#include "globals.h"
#include "pinDefs.h"
#include "ledControl.h"
#include "hueSensor.h"

// ── Helpers ───────────────────────────────────────────────────────────────

static void printGet() {
    Serial.print("freq=");            Serial.println(freq);
    Serial.print("trialLength=");     Serial.println(trialLength);
    Serial.print("interTrialWait=");  Serial.println(interTrialWait);
    Serial.print("nBaselinesStart="); Serial.println(nBaselinesStart);
    Serial.print("nBaselinesEnd=");   Serial.println(nBaselinesEnd);
    Serial.print("steps=");           Serial.println(steps);
    Serial.print("order=");           Serial.println(gridOrder);
    Serial.print("maxA=");            Serial.println(maxA);
    Serial.print("minA=");            Serial.println(minA);
    Serial.print("maxB=");            Serial.println(maxB);
    Serial.print("minB=");            Serial.println(minB);
    Serial.print("LEDA=");            Serial.println(ledIdStr(ledA));
    Serial.print("LEDB=");            Serial.println(ledIdStr(ledB));
    Serial.print("bgStim1Led=");      Serial.println(ledIdStr(bgStim1Led));
    Serial.print("bgStim1Int=");      Serial.println(bgStim1Int);
    Serial.print("bgStim2Led=");      Serial.println(ledIdStr(bgStim2Led));
    Serial.print("bgStim2Int=");      Serial.println(bgStim2Int);
    Serial.print("ref1Led=");         Serial.println(ledIdStr(ref1Led));
    Serial.print("ref1Int=");         Serial.println(ref1Int);
    Serial.print("ref2Led=");         Serial.println(ledIdStr(ref2Led));
    Serial.print("ref2Int=");         Serial.println(ref2Int);
    Serial.print("ref3Led=");         Serial.println(ledIdStr(ref3Led));
    Serial.print("ref3Int=");         Serial.println(ref3Int);
    Serial.print("baselineLed1=");    Serial.println(ledIdStr(baselineLed1));
    Serial.print("baselineLed1Val="); Serial.println(baselineLed1Val);
    Serial.print("baselineLed2=");    Serial.println(ledIdStr(baselineLed2));
    Serial.print("baselineLed2Val="); Serial.println(baselineLed2Val);
    Serial.print("baselineLed3=");    Serial.println(ledIdStr(baselineLed3));
    Serial.print("baselineLed3Val="); Serial.println(baselineLed3Val);
    Serial.print("hue=");             Serial.println(hueEnabled ? 1 : 0);
    Serial.print("REDLED=");          Serial.println((int)ledVal[LED_RED]);
    Serial.print("YELLOWLED=");       Serial.println((int)ledVal[LED_YELLOW]);
    Serial.print("GREENLED=");        Serial.println((int)ledVal[LED_GREEN]);
    Serial.print("BLUELED=");         Serial.println((int)ledVal[LED_BLUE]);
    Serial.print("CYANLED=");         Serial.println((int)ledVal[LED_CYAN]);

    const char* modeStr = "NONE";
    switch (activeMode) {
        case MODE_SOLID:      modeStr = "SOLID";      break;
        case MODE_LINEAR:     modeStr = "LINEAR";     break;
        case MODE_GRID:       modeStr = "GRID";       break;
        case MODE_BEHAVIORAL: modeStr = "BEHAVIORAL"; break;
        default: break;
    }
    Serial.print("mode="); Serial.println(modeStr);
}

static void printGetParam(const String& param) {
    if (param == "freq")            { Serial.print("freq=");            Serial.println(freq); }
    else if (param == "trialLength"){ Serial.print("trialLength=");     Serial.println(trialLength); }
    else if (param == "interTrialWait") { Serial.print("interTrialWait="); Serial.println(interTrialWait); }
    else if (param == "nBaselinesStart") { Serial.print("nBaselinesStart="); Serial.println(nBaselinesStart); }
    else if (param == "nBaselinesEnd")   { Serial.print("nBaselinesEnd=");   Serial.println(nBaselinesEnd); }
    else if (param == "steps")      { Serial.print("steps=");           Serial.println(steps); }
    else if (param == "order")      { Serial.print("order=");           Serial.println(gridOrder); }
    else if (param == "maxA")       { Serial.print("maxA=");            Serial.println(maxA); }
    else if (param == "minA")       { Serial.print("minA=");            Serial.println(minA); }
    else if (param == "maxB")       { Serial.print("maxB=");            Serial.println(maxB); }
    else if (param == "minB")       { Serial.print("minB=");            Serial.println(minB); }
    else if (param == "LEDA")       { Serial.print("LEDA=");            Serial.println(ledIdStr(ledA)); }
    else if (param == "LEDB")       { Serial.print("LEDB=");            Serial.println(ledIdStr(ledB)); }
    else if (param == "hue")        { Serial.print("hue=");             Serial.println(hueEnabled ? 1 : 0); }
    else if (param == "mode") {
        const char* modeStr = "NONE";
        switch (activeMode) {
            case MODE_SOLID:      modeStr = "SOLID";      break;
            case MODE_LINEAR:     modeStr = "LINEAR";     break;
            case MODE_GRID:       modeStr = "GRID";       break;
            case MODE_BEHAVIORAL: modeStr = "BEHAVIORAL"; break;
            default: break;
        }
        Serial.print("mode="); Serial.println(modeStr);
    }
    else { Serial.print("ERR unknown param: "); Serial.println(param); }
}

// Apply a single param=value pair. Returns false if unrecognized.
static bool applyParam(const String& p, const String& v) {
    if (p == "freq")              { freq = constrain(v.toInt(), 1, 500); updateHalfPeriod(); }
    else if (p == "trialLength")  { trialLength = (unsigned int)v.toInt(); }
    else if (p == "interTrialWait") { interTrialWait = (unsigned int)v.toInt(); }
    else if (p == "nBaselinesStart") { nBaselinesStart = v.toInt(); }
    else if (p == "nBaselinesEnd") { nBaselinesEnd = v.toInt(); }
    else if (p == "steps")        { steps = constrain(v.toInt(), 2, 50); }
    else if (p == "order")        { gridOrder = constrain(v.toInt(), 0, 4); }
    else if (p == "maxA")         { maxA = constrain(v.toInt(), 0, 4095); }
    else if (p == "minA")         { minA = constrain(v.toInt(), 0, 4095); }
    else if (p == "maxB")         { maxB = constrain(v.toInt(), 0, 4095); }
    else if (p == "minB")         { minB = constrain(v.toInt(), 0, 4095); }
    // LED-role params: reject unknown names and duplicate LEDs within the same phase
    // group (stim: LEDA/LEDB/bgStim1/bgStim2; ref: ref1/2/3; baseline: baselineLed1/2/3).
    // Cross-phase reuse (e.g. RED for both baseline and stim) is allowed.
    else if (p == "LEDA")         { if (!isValidLedName(v)) return false; LedId nv = parseLedId(v); if (ledInUse(nv, ledB, bgStim1Led, bgStim2Led)) return false; ledA = nv; }
    else if (p == "LEDB")         { if (!isValidLedName(v)) return false; LedId nv = parseLedId(v); if (ledInUse(nv, ledA, bgStim1Led, bgStim2Led)) return false; ledB = nv; }
    else if (p == "bgStim1Led")   { if (!isValidLedName(v)) return false; LedId nv = parseLedId(v); if (ledInUse(nv, ledA, ledB, bgStim2Led)) return false; bgStim1Led = nv; }
    else if (p == "bgStim1Int")   { bgStim1Int = constrain(v.toInt(), 0, 4095); }
    else if (p == "bgStim2Led")   { if (!isValidLedName(v)) return false; LedId nv = parseLedId(v); if (ledInUse(nv, ledA, ledB, bgStim1Led)) return false; bgStim2Led = nv; }
    else if (p == "bgStim2Int")   { bgStim2Int = constrain(v.toInt(), 0, 4095); }
    else if (p == "ref1Led")      { if (!isValidLedName(v)) return false; LedId nv = parseLedId(v); if (ledInUse(nv, ref2Led, ref3Led)) return false; ref1Led = nv; }
    else if (p == "ref1Int")      { ref1Int = constrain(v.toInt(), 0, 4095); }
    else if (p == "ref2Led")      { if (!isValidLedName(v)) return false; LedId nv = parseLedId(v); if (ledInUse(nv, ref1Led, ref3Led)) return false; ref2Led = nv; }
    else if (p == "ref2Int")      { ref2Int = constrain(v.toInt(), 0, 4095); }
    else if (p == "ref3Led")      { if (!isValidLedName(v)) return false; LedId nv = parseLedId(v); if (ledInUse(nv, ref1Led, ref2Led)) return false; ref3Led = nv; }
    else if (p == "ref3Int")      { ref3Int = constrain(v.toInt(), 0, 4095); }
    else if (p == "baselineLed1")    { if (!isValidLedName(v)) return false; LedId nv = parseLedId(v); if (ledInUse(nv, baselineLed2, baselineLed3)) return false; baselineLed1 = nv; }
    else if (p == "baselineLed1Val") { baselineLed1Val = constrain(v.toInt(), 0, 4095); }
    else if (p == "baselineLed2")    { if (!isValidLedName(v)) return false; LedId nv = parseLedId(v); if (ledInUse(nv, baselineLed1, baselineLed3)) return false; baselineLed2 = nv; }
    else if (p == "baselineLed2Val") { baselineLed2Val = constrain(v.toInt(), 0, 4095); }
    else if (p == "baselineLed3")    { if (!isValidLedName(v)) return false; LedId nv = parseLedId(v); if (ledInUse(nv, baselineLed1, baselineLed2)) return false; baselineLed3 = nv; }
    else if (p == "baselineLed3Val") { baselineLed3Val = constrain(v.toInt(), 0, 4095); }
    else if (p == "hue")          { if (activeMode == MODE_BEHAVIORAL) return false; hueEnabled = (v.toInt() != 0); }
    // Solid-mode direct LED values — also applied live if running solid
    else if (p == "REDLED")    { int val = constrain(v.toInt(), 0, 4095); ledVal[LED_RED]    = val; if (activeMode == MODE_SOLID && fwState == STATE_RUNNING) analogWrite(PIN_RED,    val); }
    else if (p == "YELLOWLED") { int val = constrain(v.toInt(), 0, 4095); ledVal[LED_YELLOW] = val; if (activeMode == MODE_SOLID && fwState == STATE_RUNNING) analogWrite(PIN_YELLOW, val); }
    else if (p == "GREENLED")  { int val = constrain(v.toInt(), 0, 4095); ledVal[LED_GREEN]  = val; if (activeMode == MODE_SOLID && fwState == STATE_RUNNING) analogWrite(PIN_GREEN,  val); }
    else if (p == "BLUELED")   { int val = constrain(v.toInt(), 0, 4095); ledVal[LED_BLUE]   = val; if (activeMode == MODE_SOLID && fwState == STATE_RUNNING) analogWrite(PIN_BLUE,   val); }
    else if (p == "CYANLED")   { int val = constrain(v.toInt(), 0, 4095); ledVal[LED_CYAN]   = val; if (activeMode == MODE_SOLID && fwState == STATE_RUNNING) analogWrite(PIN_CYAN,   val); }
    else return false;

    return true;
}

// Parse "param value" token (space-separated). Returns false if malformed or unknown.
static bool applyToken(const String& token) {
    int sp = token.indexOf(' ');
    if (sp < 0) return false;
    String p = token.substring(0, sp);
    String v = token.substring(sp + 1);
    p.trim(); v.trim();
    if (p.length() == 0 || v.length() == 0) return false;
    return applyParam(p, v);
}

// ── Command handlers ──────────────────────────────────────────────────────

static void handleMode(const String& arg) {
    Mode newMode = MODE_NONE;
    if (arg.equalsIgnoreCase("SOLID"))      newMode = MODE_SOLID;
    else if (arg.equalsIgnoreCase("LINEAR"))     newMode = MODE_LINEAR;
    else if (arg.equalsIgnoreCase("GRID"))       newMode = MODE_GRID;
    else if (arg.equalsIgnoreCase("BEHAVIORAL")) newMode = MODE_BEHAVIORAL;
    else { Serial.print("ERR unknown mode: "); Serial.println(arg); return; }

    activeMode = newMode;
    applyDefaults();
    fwState = STATE_CONFIGURED;
    Serial.print("OK MODE "); Serial.println(arg);
}

static void handleSet(const String& body) {
    // body is one or more "param value" pairs separated by ", "
    int pos = 0;
    while (pos <= (int)body.length()) {
        int sep = body.indexOf(", ", pos);
        String tok = (sep < 0) ? body.substring(pos) : body.substring(pos, sep);
        tok.trim();
        if (tok.length() > 0) {
            if (!applyToken(tok)) {
                Serial.print("ERR unknown param: "); Serial.println(tok);
            } else {
                int sp = tok.indexOf(' ');
                Serial.print("OK SET "); Serial.println(tok.substring(0, sp));
            }
        }
        if (sep < 0) break;
        pos = sep + 2;
    }
}

static void handleStart() {
    if (activeMode == MODE_NONE) {
        Serial.println("ERR no mode selected");
        return;
    }
    if (hueEnabled) {
        if (!initHueSensor()) {
            Serial.println("ERR hue sensor not connected");
            return;
        }
    }
    trCnt    = 0;
    trigFlag = 0;
    pressFlag = false;
    guiPressRequest = false;
    started  = true;
    fwState  = STATE_RUNNING;
    Serial.println("OK START");
}

// ── Main entry point ──────────────────────────────────────────────────────

void handleSerial() {
    if (!Serial.available()) return;

    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() == 0) return;

    // STOP — accepted from any state
    if (cmd.equalsIgnoreCase("STOP")) {
        started   = false;
        fwState   = STATE_IDLE;
        activeMode = MODE_NONE;
        allLedsOff();
        trigFlag  = 0;
        digitalWrite(PIN_TRIGGER, LOW);
        Serial.println("OK STOP");
        return;
    }

    // GET [param] — accepted from any state
    if (cmd.equalsIgnoreCase("GET")) {
        printGet();
        return;
    }
    if (cmd.startsWith("GET ") || cmd.startsWith("get ")) {
        String param = cmd.substring(4);
        param.trim();
        printGetParam(param);
        return;
    }

    // MODE — accepted in IDLE or CONFIGURED
    if (cmd.startsWith("MODE ") || cmd.startsWith("mode ")) {
        if (fwState == STATE_RUNNING) { Serial.println("ERR busy"); return; }
        String arg = cmd.substring(5); arg.trim();
        handleMode(arg);
        return;
    }

    // SET — accepted in CONFIGURED, or in RUNNING only for solid LED values
    if (cmd.startsWith("SET ") || cmd.startsWith("set ")) {
        if (fwState == STATE_IDLE) { Serial.println("ERR no mode selected"); return; }
        if (fwState == STATE_RUNNING && activeMode != MODE_SOLID) { Serial.println("ERR busy"); return; }
        String body = cmd.substring(4); body.trim();
        handleSet(body);
        return;
    }

    // START — accepted in CONFIGURED
    if (cmd.equalsIgnoreCase("START")) {
        if (fwState != STATE_CONFIGURED) {
            Serial.println(fwState == STATE_IDLE ? "ERR no mode selected" : "ERR busy");
            return;
        }
        handleStart();
        return;
    }

    // PRESS — GUI-side button press (Solid or Behavioral mode only, while running)
    if (cmd.equalsIgnoreCase("PRESS")) {
        if (fwState == STATE_RUNNING && activeMode == MODE_SOLID) {
            trCnt++;
            pressFlag = true;
            Serial.println("OK PRESS");
        } else if (fwState == STATE_RUNNING && activeMode == MODE_BEHAVIORAL) {
            // Consumed by runBehavioral(), which mirrors the physical button path
            guiPressRequest = true;
            Serial.println("OK PRESS");
        } else {
            Serial.println("ERR PRESS only valid in SOLID or BEHAVIORAL mode while running");
        }
        return;
    }

    Serial.print("ERR unknown command: "); Serial.println(cmd);
}
