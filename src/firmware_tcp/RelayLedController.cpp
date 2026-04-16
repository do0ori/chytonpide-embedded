#include "RelayLedController.h"

void RelayLedController::begin(uint8_t relayPin, uint8_t comPin) {
  relaySignalPin = relayPin;
  relayComPin = comPin;

  if (relaySignalPin != 0xFF) {
    pinMode(relaySignalPin, OUTPUT);
    digitalWrite(relaySignalPin, LOW);
  }

  if (relayComPin != 0xFF) {
    pinMode(relayComPin, OUTPUT);
    digitalWrite(relayComPin, LOW);
  }

  currentRelayState = false;
  initialized = true;
}

void RelayLedController::applyLedState(bool isLedOn) {
  if (!initialized || relaySignalPin == 0xFF) {
    return;
  }

  if (isLedOn != currentRelayState) {
    digitalWrite(relaySignalPin, isLedOn ? HIGH : LOW);
    currentRelayState = isLedOn;
    Serial.printf("[LED] Relay %s\n", isLedOn ? "ON" : "OFF");
  }
}
