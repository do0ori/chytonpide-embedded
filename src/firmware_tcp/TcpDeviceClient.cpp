#include "TcpDeviceClient.h"

TcpDeviceClient::TcpDeviceClient(const char* serverHost, uint16_t serverPort, const char* serial)
  : host(serverHost),
    port(serverPort),
    serialId(serial),
    lineBuffer(""),
    lastReconnectAttempt(0),
    reconnectInterval(INITIAL_RECONNECT_MS),
    lastActivity(0),
    stateCallback(nullptr) {
}

void TcpDeviceClient::begin() {
  tryReconnect();
}

void TcpDeviceClient::poll() {
  if (!client.connected()) {
    tryReconnect();
    return;
  }

  // Non-blocking read: only process bytes already in the buffer
  while (client.available()) {
    char c = client.read();
    if (c == '\n') {
      if (lineBuffer.length() > 0) {
        processLine(lineBuffer);
        lineBuffer = "";
      }
    } else {
      if (lineBuffer.length() < MAX_LINE_LENGTH) {
        lineBuffer += c;
      } else {
        // Abnormally long message — reset buffer
        lineBuffer = "";
      }
    }
  }

  // Keepalive timeout: if no data from server for too long, reconnect
  if (millis() - lastActivity > ACTIVITY_TIMEOUT_MS) {
    Serial.println("[TCP] Activity timeout, reconnecting...");
    client.stop();
    lineBuffer = "";
    tryReconnect();
  }
}

void TcpDeviceClient::tryReconnect() {
  unsigned long now = millis();
  if (now - lastReconnectAttempt < reconnectInterval) {
    return;  // Not time yet
  }
  lastReconnectAttempt = now;

  if (WiFi.status() != WL_CONNECTED) {
    return;  // No WiFi
  }

  Serial.printf("[TCP] Connecting to %s:%d...\n", host, port);

  if (client.connect(host, port)) {
    Serial.println("[TCP] Connected!");
    client.setNoDelay(true);
    reconnectInterval = INITIAL_RECONNECT_MS;  // Reset backoff
    lastActivity = millis();
    sendHello();
  } else {
    Serial.println("[TCP] Connection failed");
    // Exponential backoff
    reconnectInterval = min(reconnectInterval * 2, MAX_RECONNECT_MS);
    Serial.printf("[TCP] Next retry in %lu ms\n", reconnectInterval);
  }
}

void TcpDeviceClient::sendHello() {
  JsonDocument doc;
  doc["type"] = "hello";
  doc["serial"] = serialId;
  sendJson(doc);
}

void TcpDeviceClient::sendSensorData(float temperature, float humidity, int illuminance) {
  if (!client.connected()) {
    return;
  }

  JsonDocument doc;
  doc["type"] = "sensor_data";
  doc["serial"] = serialId;
  doc["temperature"] = serialized(String(temperature, 2));
  doc["humidity"] = serialized(String(humidity, 2));
  doc["illuminance"] = illuminance;
  sendJson(doc);
}

void TcpDeviceClient::sendJson(JsonDocument& doc) {
  if (!client.connected()) {
    return;
  }

  String msg;
  serializeJson(doc, msg);
  msg += "\n";
  client.print(msg);
}

void TcpDeviceClient::processLine(const String& line) {
  lastActivity = millis();

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, line);
  if (err) {
    Serial.printf("[TCP] JSON parse error: %s\n", err.c_str());
    return;
  }

  const char* type = doc["type"];
  if (!type) {
    return;
  }

  if (strcmp(type, "hello_ack") == 0) {
    handleHelloAck(doc);
  } else if (strcmp(type, "state_update") == 0) {
    handleStateUpdate(doc);
  } else if (strcmp(type, "ping") == 0) {
    // Respond with pong
    JsonDocument pong;
    pong["type"] = "pong";
    sendJson(pong);
  } else if (strcmp(type, "ack") == 0) {
    // Sensor data acknowledged — nothing to do
  } else if (strcmp(type, "error") == 0) {
    const char* message = doc["message"] | "unknown";
    Serial.printf("[TCP] Server error: %s\n", message);
  }
}

void TcpDeviceClient::handleHelloAck(JsonDocument& doc) {
  Serial.println("[TCP] hello_ack received");

  if (stateCallback) {
    bool hasLed = doc.containsKey("is_led_on");
    bool isLedOn = doc["is_led_on"] | false;
    bool hasFace = doc.containsKey("face");
    String face = doc["face"] | "NEUTRAL";
    stateCallback(hasLed, isLedOn, hasFace, face);
  }
}

void TcpDeviceClient::handleStateUpdate(JsonDocument& doc) {
  Serial.println("[TCP] state_update received");

  if (stateCallback) {
    bool hasLed = doc.containsKey("is_led_on");
    bool isLedOn = doc["is_led_on"] | false;
    bool hasFace = doc.containsKey("face");
    String face = doc["face"] | "NEUTRAL";
    stateCallback(hasLed, isLedOn, hasFace, face);
  }
}
