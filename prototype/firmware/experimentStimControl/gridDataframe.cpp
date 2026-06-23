#include <Arduino.h>

#include "gridDataframe.h"

void gridSendDataFrame(int triggerCue, int stimNumber, int amberValue,
                        int redValue, int greenValue, int phase) {
  Serial.print(triggerCue);
  Serial.print('@');
  Serial.print(stimNumber);
  Serial.print('@');
  Serial.print(amberValue);
  Serial.print('@');
  Serial.print(redValue);
  Serial.print('@');
  Serial.print(greenValue);
  Serial.print('@');
  Serial.println(phase);
}
