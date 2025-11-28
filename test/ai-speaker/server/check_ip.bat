@echo off
echo ========================================
echo 로컬 IP 주소 확인
echo ========================================
echo.

echo [방법 1: ipconfig]
ipconfig | findstr /i "IPv4"

echo.
echo [방법 2: 상세 정보]
ipconfig /all | findstr /i "IPv4"

echo.
echo [현재 활성 네트워크 어댑터]
ipconfig | findstr /i /C:"어댑터" /C:"Adapter"

echo.
echo ========================================
echo 찾은 IP 주소 중 "192.168.x.x" 또는 "10.x.x.x" 형식을 사용하세요
echo ========================================
pause


