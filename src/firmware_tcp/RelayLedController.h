#ifndef RELAY_LED_CONTROLLER_H
#define RELAY_LED_CONTROLLER_H

#include <Arduino.h>

/**
 * RelayLedController (TCP version)
 * -------------------
 * HTTP polling을 제거하고, 서버 push로 받은 상태를 릴레이에 적용하는 액추에이터.
 * TcpDeviceClient의 state_update 콜백에서 applyLedState()를 호출한다.
 */
class RelayLedController {
public:
  void begin(uint8_t relayPin, uint8_t relayComPin = 0xFF);
  void applyLedState(bool isLedOn);
  bool getCurrentState() const { return currentRelayState; }

private:
  uint8_t relaySignalPin = 0xFF;
  uint8_t relayComPin = 0xFF;
  bool currentRelayState = false;
  bool initialized = false;
};

#endif
