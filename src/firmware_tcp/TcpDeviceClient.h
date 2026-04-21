#ifndef TCP_DEVICE_CLIENT_H
#define TCP_DEVICE_CLIENT_H

#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoJson.h>

// Callback type for state_update messages
typedef void (*StateUpdateCallback)(bool hasLed, bool isLedOn, bool hasFace, const String& face);

class TcpDeviceClient {
public:
  TcpDeviceClient(const char* serverHost, uint16_t serverPort, const char* serial);

  // Call once in setup() after WiFi is connected
  void begin();

  // Call every loop() iteration — non-blocking
  void poll();

  // Send sensor data to server
  void sendSensorData(float temperature, float humidity, int illuminance);

  // Register callback for state_update / hello_ack
  void onStateUpdate(StateUpdateCallback cb) { stateCallback = cb; }

  // Connection state
  bool isConnected() { return client.connected(); }

private:
  // Server config
  const char* host;
  uint16_t port;
  const char* serialId;

  // TCP connection
  WiFiClient client;
  String lineBuffer;

  // Reconnection backoff
  unsigned long lastReconnectAttempt;
  unsigned long reconnectInterval;
  static const unsigned long INITIAL_RECONNECT_MS = 1000;
  static const unsigned long MAX_RECONNECT_MS = 30000;

  // Keepalive
  unsigned long lastActivity;
  static const unsigned long ACTIVITY_TIMEOUT_MS = 60000;

  // Line buffer limit
  static const size_t MAX_LINE_LENGTH = 1024;

  // State callback
  StateUpdateCallback stateCallback;

  // Internal methods
  void tryReconnect();
  void sendHello();
  void sendJson(JsonDocument& doc);
  void processLine(const String& line);
  void handleHelloAck(JsonDocument& doc);
  void handleStateUpdate(JsonDocument& doc);
};

#endif
