# 🔨 Compile

-   VS Code의 [Arduino Maker Workshop](https://marketplace.visualstudio.com/items?itemName=TheLastOutpostWorkshop.arduino-maker-workshop) extension 사용
-   Board: ESP32 Dev Module

# 📤 Upload

-   [**Flash Download Tool**](https://docs.espressif.com/projects/esp-test-tools/en/latest/esp32/production_stage/tools/flash_download_tool.html) 다운로드
    -   ChipType: ESP32-S3
    -   WorkMode: Develop
    -   LoadMode: USB
-   compile해서 나온 bin 파일을 보드에 업로드 (boot 핀 누른 상태에서 rst 핀 눌렀다 떼기)
    ![upload](https://github.com/user-attachments/assets/9d3b2f7d-9ae0-47d1-9092-d6a1017df67d)

> https://www.notion.so/ESP32-S3-R8N16-2aa9b91d60ce8018ab8fd91825a3fa76 참고
