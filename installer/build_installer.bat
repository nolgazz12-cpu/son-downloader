@echo off
chcp 65001 >nul
echo ========================================
echo   설치 프로그램 빌드
echo ========================================
echo.

cd /d "%~dp0"

:: 1. Native Host 빌드
echo [1/2] Native Host 빌드 중...
cd ..\native_host
pyinstaller --onefile --noconsole --name=native_host native_host.py
if errorlevel 1 (
    echo Native Host 빌드 실패
    pause
    exit /b 1
)
copy /y "dist\native_host.exe" "..\installer\native_host.exe" >nul
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del native_host.spec 2>nul

:: 2. 설치 프로그램 빌드 (chrome_extension 폴더 포함)
echo [2/2] 설치 프로그램 빌드 중...
cd ..\installer
pyinstaller --onefile --name=SonDownloader_Setup ^
    --add-data "native_host.exe;." ^
    --add-data "..\chrome_extension;chrome_extension" ^
    setup.py
if errorlevel 1 (
    echo 설치 프로그램 빌드 실패
    pause
    exit /b 1
)

:: 결과물 정리
copy /y "dist\SonDownloader_Setup.exe" "..\SonDownloader_Setup.exe" >nul
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del SonDownloader_Setup.spec 2>nul
del native_host.exe 2>nul

echo.
echo ========================================
echo   빌드 완료!
echo ========================================
echo.
echo 결과물: SonDownloader_Setup.exe
echo.
pause
