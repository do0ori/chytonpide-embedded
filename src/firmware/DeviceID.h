#ifndef DEVICE_ID_H
#define DEVICE_ID_H

#include <Preferences.h>
#include <WiFi.h>
#include <esp_system.h>

class DeviceID {
private:
  Preferences preferences;
  static const char* NAMESPACE;
  static const char* KEY_CUSTOM_ID;
  
  // 하드웨어 고유 ID 생성 (Chip ID 기반)
  String getHardwareID() {
    // ESP32-S3의 Efuse MAC 주소 사용 (고유하고 변경 불가능)
    uint64_t chipid = ESP.getEfuseMac();
    
    // 64비트를 16진수 문자열로 변환 (예: "A1B2C3D4E5F6")
    char hwId[17];
    snprintf(hwId, sizeof(hwId), "%016llX", chipid);
    
    return String(hwId);
  }
  
  // MAC 주소 기반 ID 생성 (대안)
  String getMACID() {
    uint8_t mac[6];
    WiFi.macAddress(mac);
    
    char macId[18];
    snprintf(macId, sizeof(macId), "%02X%02X%02X%02X%02X%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    
    return String(macId);
  }

public:
  DeviceID() {
    // read-write 모드로 열어야 setCustomID()가 작동함
    preferences.begin(NAMESPACE, false);
  }
  
  ~DeviceID() {
    preferences.end();
  }
  
  // 기기 ID 가져오기 (사용자 정의 ID가 있으면 그것을, 없으면 하드웨어 ID 사용)
  String getID() {
    String customId = preferences.getString(KEY_CUSTOM_ID, "");
    
    if (customId.length() > 0) {
      return customId;
    }
    
    // 기본값: 하드웨어 ID 사용
    return getHardwareID();
  }
  
  // 하드웨어 고유 ID만 가져오기 (읽기 전용)
  String getHardwareIDOnly() {
    return getHardwareID();
  }
  
  // 사용자 정의 ID 설정
  bool setCustomID(const String& customId) {
    if (customId.length() == 0) {
      // 빈 문자열이면 사용자 정의 ID 삭제
      return clearCustomID();
    }
    
    // ID 유효성 검사 (예: 최대 32자, 영숫자와 하이픈만 허용)
    if (customId.length() > 32) {
      return false;
    }
    
    for (size_t i = 0; i < customId.length(); i++) {
      char c = customId.charAt(i);
      if (!isalnum(c) && c != '-' && c != '_') {
        return false;
      }
    }
    
    // 기존 값이 있으면 먼저 삭제
    preferences.remove(KEY_CUSTOM_ID);
    
    // 새 값 저장
    size_t written = preferences.putString(KEY_CUSTOM_ID, customId);
    return (written > 0);
  }
  
  // 사용자 정의 ID 삭제 (하드웨어 ID로 되돌림)
  bool clearCustomID() {
    return preferences.remove(KEY_CUSTOM_ID);
  }
  
  // 사용자 정의 ID가 설정되어 있는지 확인
  bool hasCustomID() {
    return preferences.getString(KEY_CUSTOM_ID, "").length() > 0;
  }
  
  // 짧은 ID 생성 (하드웨어 ID의 마지막 8자리)
  String getShortID() {
    String fullId = getID();
    if (fullId.length() > 8) {
      return fullId.substring(fullId.length() - 8);
    }
    return fullId;
  }
};

#endif

