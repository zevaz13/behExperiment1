#include "hueSensor.h"
#include "globals.h"

static Adafruit_TCS34725 tcs = Adafruit_TCS34725(
    TCS34725_INTEGRATIONTIME_101MS, TCS34725_GAIN_16X);

bool initHueSensor() {
    if (!tcs.begin()) {
        hueR = hueG = hueB = hueCT = hueL = -99;
        return false;
    }
    return true;
}

void readHue() {
    uint16_t r, g, b, c;
    tcs.getRawData(&r, &g, &b, &c);
    hueR  = (int)r;
    hueG  = (int)g;
    hueB  = (int)b;
    hueCT = (int)tcs.calculateColorTemperature_dn40(r, g, b, c);
    hueL  = (int)tcs.calculateLux(r, g, b);
}
