#ifndef WIFI_STATE_H
#define WIFI_STATE_H

// WiFi 상태
enum WifiState {
  WIFI_CONNECTING,    // WiFi 연결 시도 중
  WIFI_CONFIG_MODE,   // AP 모드 (설정 필요)
  WIFI_CONNECTED,     // WiFi 연결 성공
  WIFI_ERROR          // 에러 상태
};

#endif

