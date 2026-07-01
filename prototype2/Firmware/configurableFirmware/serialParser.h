#ifndef SERIAL_PARSER_H
#define SERIAL_PARSER_H

// Called from loop() whenever Serial.available(). Reads and processes one command.
void handleSerial();

#endif
