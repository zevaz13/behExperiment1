#ifndef HUE_SENSOR_H
#define HUE_SENSOR_H

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_TCS34725.h>

// Attempt to initialise the sensor. Returns true if found, false if not.
// On success updates hueR/G/B/CT/L globals; on failure leaves them at -99.
bool initHueSensor();

// Read sensor and update hueR, hueG, hueB, hueCT, hueL globals.
// Call from loop() when hueEnabled is true.
void readHue();

#endif
