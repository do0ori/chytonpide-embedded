#include "RelayLedController.h"
#include <ctype.h>

RelayLedController::RelayLedController(const char* baseUrl, const char* stateEndpoint, DeviceID* deviceRef)
  : serverBaseUrl(baseUrl),
    ledStateEndpoint(stateEndpoint),
    device(deviceRef),
    relaySignalPin(0xFF),
    relayComPin(0xFF),
    currentRelayState(false),
    initialized(false),
    lastCheckTime(0),
    checkIntervalMs(2000) {
}

void RelayLedController::begin(uint8_t relayPin, uint8_t comPin) {
  relaySignalPin = relayPin;
  relayComPin = comPin;

  ensurePinsInitialized();
  initialized = true;
}

void RelayLedController::ensurePinsInitialized() {
  if (relaySignalPin != 0xFF) {
    pinMode(relaySignalPin, OUTPUT);
    digitalWrite(relaySignalPin, LOW);
    currentRelayState = false;
  }

  if (relayComPin != 0xFF) {
    pinMode(relayComPin, OUTPUT);
    digitalWrite(relayComPin, LOW);
  }
}

void RelayLedController::update() {
  if (!initialized) {
    return;
  }

  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  unsigned long now = millis();
  if (now - lastCheckTime < checkIntervalMs) {
    return;
  }
  lastCheckTime = now;

  fetchAndApplyLedState();
}

void RelayLedController::fetchAndApplyLedState() {
  if (!device || !serverBaseUrl || !ledStateEndpoint) {
    return;
  }

  String deviceId = device->getID();
  if (deviceId.length() == 0) {
    return;
  }

  HTTPClient http;
  String encodedDeviceId = urlEncode(deviceId);
  String url = String(serverBaseUrl) + ledStateEndpoint + "?device_id=" + encodedDeviceId;

  http.begin(url);
  int httpCode = http.GET();

  if (httpCode == HTTP_CODE_OK) {
    String response = http.getString();
    int parsedState = parseLedStateFromJson(response);
    if (parsedState != -1) {
      bool serverLedState = (parsedState == 1);
      if (serverLedState != currentRelayState) {
        setRelayState(serverLedState);
      }
    }
  }

  http.end();
}

int RelayLedController::parseLedStateFromJson(const String& json) const {
  int ledOnIndex = json.indexOf("\"led_on\":");
  if (ledOnIndex == -1) {
    return -1;
  }

  int valueStart = json.indexOf(':', ledOnIndex) + 1;
  while (valueStart < json.length() && isspace(json.charAt(valueStart))) {
    valueStart++;
  }

  if (json.substring(valueStart, valueStart + 4).equalsIgnoreCase("true")) {
    return 1;
  }
  if (json.substring(valueStart, valueStart + 5).equalsIgnoreCase("false")) {
    return 0;
  }

  return -1;
}

void RelayLedController::setRelayState(bool turnOn) {
  if (relaySignalPin == 0xFF) {
    return;
  }
  digitalWrite(relaySignalPin, turnOn ? HIGH : LOW);
  currentRelayState = turnOn;
}

String RelayLedController::urlEncode(const String& raw) const {
  String encoded = "";
  for (size_t i = 0; i < raw.length(); ++i) {
    char c = raw.charAt(i);
    if (isalnum(static_cast<unsigned char>(c)) || c == '-' || c == '_' || c == '.' || c == '~') {
      // 안전한 문자는 그대로 유지 (대소문자 보존)
      encoded += c;
    } else {
      // 특수 문자는 퍼센트 인코딩 (HEX는 대문자로 변환)
      encoded += '%';
      if ((uint8_t)c < 0x10) encoded += '0';
      String hex = String(static_cast<uint8_t>(c), HEX);
      hex.toUpperCase();
      encoded += hex;
    }
  }
  return encoded;
}

