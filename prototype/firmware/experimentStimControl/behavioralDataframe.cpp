#include <Arduino.h>

#include "behavioralDataframe.h"

void behavioralSendDataFrame(int amberValue, int redValue, int greenValue, int press, int trialNumber) {
  Serial.print(0);
  Serial.print('@');
  Serial.print(trialNumber);
  Serial.print('@');
  Serial.print(amberValue);
  Serial.print('@');
  Serial.print(redValue);
  Serial.print('@');
  Serial.print(greenValue);
  Serial.print('@');
  Serial.println(press);
}
