@echo off
chcp 65001 >nul
echo ========================================
echo   Native Host 빌드
echo ========================================
echo.

:: 현재 디렉토리로 이동
cd /d "%~dp0"

:: PyInstaller로 exe 빌드
echo PyInstaller로 빌드 중...
pyinstaller --onefile --noconsole --name=native_host native_host.py

:: 빌드된 exe 복사
if exist "dist\native_host.exe" (
    copy /y "dist\native_host.exe" "native_host.exe" >nul
    echo.
    echo 빌드 완료: native_host.exe

    :: 정리
    rmdir /s /q build 2>nul
    rmdir /s /q dist 2>nul
    del native_host.spec 2>nul
) else (
    echo 빌드 실패
)

echo.
pause
