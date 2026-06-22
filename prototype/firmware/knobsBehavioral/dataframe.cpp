#include <Arduino.h>

#include "dataframe.h"

void sendDataFrame(int amberValue, int redValue, int greenValue, int press) {
  Serial.print(0);
  Serial.print('@');
  Serial.print(0);
  Serial.print('@');
  Serial.print(amberValue);
  Serial.print('@');
  Serial.print(redValue);
  Serial.print('@');
  Serial.print(greenValue);
  Serial.print('@');
  Serial.println(press);
}
