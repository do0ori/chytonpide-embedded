#!/bin/bash
echo "========================================"
echo "로컬 IP 주소 확인"
echo "========================================"
echo ""

# Windows (Git Bash/MINGW)
if command -v ipconfig &> /dev/null; then
    echo "[Windows - ipconfig 결과]"
    ipconfig | grep -i "IPv4"
    echo ""
    echo "WiFi 어댑터의 IP 주소를 찾으세요 (보통 '무선 LAN 어댑터' 또는 'Wireless LAN adapter')"
fi

# Linux/Mac
if command -v hostname &> /dev/null && command -v hostname -I &> /dev/null; then
    echo "[Linux/Mac - hostname 결과]"
    hostname -I
fi

if command -v ifconfig &> /dev/null; then
    echo "[ifconfig 결과]"
    ifconfig | grep -E "inet [0-9]" | grep -v "127.0.0.1"
fi

echo ""
echo "========================================"
echo "찾은 IP 주소 중 '192.168.x.x' 형식을 사용하세요"
echo "========================================"


