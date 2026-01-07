@echo off
chcp 65001 >nul
echo ========================================
echo   손 다운로더 Native Host 설치
echo ========================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 관리자 권한이 필요합니다.
    echo 이 파일을 우클릭하고 "관리자 권한으로 실행"을 선택하세요.
    pause
    exit /b 1
)

:: 현재 디렉토리
set "SCRIPT_DIR=%~dp0"
set "NATIVE_HOST_PATH=%SCRIPT_DIR%native_host.exe"
set "MANIFEST_PATH=%SCRIPT_DIR%com.son.downloader.json"

:: native_host.exe 존재 확인
if not exist "%NATIVE_HOST_PATH%" (
    echo native_host.exe를 찾을 수 없습니다.
    echo 먼저 build.bat을 실행하여 빌드해주세요.
    pause
    exit /b 1
)

:: manifest.json 업데이트
echo 설정 파일 업데이트 중...

:: 확장프로그램 ID 입력 받기
echo.
echo Chrome 확장프로그램 ID를 입력하세요.
echo (chrome://extensions 에서 확인 가능)
echo.
set /p EXTENSION_ID="확장프로그램 ID: "

if "%EXTENSION_ID%"=="" (
    echo ID를 입력해야 합니다.
    pause
    exit /b 1
)

:: manifest.json 생성
echo {> "%MANIFEST_PATH%"
echo   "name": "com.son.downloader",>> "%MANIFEST_PATH%"
echo   "description": "YouTube Downloader Native Host",>> "%MANIFEST_PATH%"
echo   "path": "%NATIVE_HOST_PATH:\=\\%",>> "%MANIFEST_PATH%"
echo   "type": "stdio",>> "%MANIFEST_PATH%"
echo   "allowed_origins": [>> "%MANIFEST_PATH%"
echo     "chrome-extension://%EXTENSION_ID%/">> "%MANIFEST_PATH%"
echo   ]>> "%MANIFEST_PATH%"
echo }>> "%MANIFEST_PATH%"

:: 레지스트리 등록
echo.
echo 레지스트리 등록 중...
reg add "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.son.downloader" /ve /t REG_SZ /d "%MANIFEST_PATH%" /f

if %errorLevel% equ 0 (
    echo.
    echo ========================================
    echo   설치 완료!
    echo ========================================
    echo.
    echo 이제 Chrome을 재시작하고 확장프로그램을 사용하세요.
) else (
    echo.
    echo 레지스트리 등록 실패
)

echo.
pause
