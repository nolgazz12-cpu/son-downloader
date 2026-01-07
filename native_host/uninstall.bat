@echo off
chcp 65001 >nul
echo ========================================
echo   손 다운로더 Native Host 제거
echo ========================================
echo.

:: 레지스트리에서 제거
reg delete "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.son.downloader" /f 2>nul

echo.
echo 제거 완료!
echo.
pause
