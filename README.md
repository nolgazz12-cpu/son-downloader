# 손 다운로더

YouTube 동영상을 다운로드하는 Chrome 확장프로그램입니다.

## 설치 방법

### 방법 1: 설치 프로그램 사용 (권장)

1. `SonDownloader_Setup.exe` 실행
2. 안내에 따라 Chrome 확장프로그램 설치
3. 확장프로그램 ID 입력
4. 완료!

### 방법 2: 수동 설치

#### 1. 확장프로그램 설치
1. Chrome에서 `chrome://extensions` 열기
2. 오른쪽 상단 **개발자 모드** 켜기
3. **압축해제된 확장 프로그램을 로드합니다** 클릭
4. `chrome_extension` 폴더 선택
5. 확장프로그램 ID 복사 (예: `abcdefghijklmnopqrstuvwxyz`)

#### 2. Native Host 설치
1. `native_host` 폴더에서 `build.bat` 실행 (exe 빌드)
2. `install.bat` **관리자 권한으로** 실행
3. 복사한 확장프로그램 ID 입력

#### 3. Chrome 재시작

## 사용 방법

1. YouTube에서 동영상 재생
2. 영상 아래 **다운로드** 버튼 클릭
3. 또는 확장프로그램 아이콘 클릭 후 다운로드

## 다운로드 위치

`내 PC > 동영상` 폴더에 저장됩니다.

## 제거 방법

1. `SonDownloader_Setup.exe` 실행 후 **제거** 선택
2. 또는 `native_host/uninstall.bat` 실행
3. Chrome에서 확장프로그램 삭제

## 빌드 방법 (개발자용)

```bash
cd installer
build_installer.bat
```

결과물: `SonDownloader_Setup.exe`
