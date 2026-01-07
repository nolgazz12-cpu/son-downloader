"""
손 다운로더 설치 프로그램
- Native Host 설치
- 확장프로그램 설치
- 레지스트리 등록
"""
import os
import sys
import json
import shutil
import winreg
import subprocess
import webbrowser
from pathlib import Path

# 설치 경로
INSTALL_DIR = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'SonDownloader')
EXTENSION_DIR = os.path.join(INSTALL_DIR, 'chrome_extension')
NATIVE_HOST_NAME = 'com.son.downloader'
# 고정된 확장프로그램 ID (manifest.json의 key로 결정됨)
EXTENSION_ID = 'ooinnigfghegnekjgodgpjlakfgbpehc'

def get_resource_path(filename):
    """PyInstaller 빌드시 리소스 경로"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(__file__), filename)

def install_extension():
    """확장프로그램 파일 설치"""
    print("확장프로그램 설치 중...")

    # 확장프로그램 디렉토리 생성
    os.makedirs(EXTENSION_DIR, exist_ok=True)

    # 확장프로그램 파일들 복사
    src_ext = get_resource_path('chrome_extension')
    if os.path.exists(src_ext):
        # 기존 파일 삭제 후 복사
        if os.path.exists(EXTENSION_DIR):
            shutil.rmtree(EXTENSION_DIR)
        shutil.copytree(src_ext, EXTENSION_DIR)
        print(f"  → {EXTENSION_DIR}")
        return True
    else:
        print("  오류: chrome_extension 폴더를 찾을 수 없습니다.")
        return False

def install_native_host():
    """Native Host 설치"""
    print("Native Host 설치 중...")

    # 설치 디렉토리 생성
    os.makedirs(INSTALL_DIR, exist_ok=True)

    # native_host.exe 복사
    src_exe = get_resource_path('native_host.exe')
    dst_exe = os.path.join(INSTALL_DIR, 'native_host.exe')

    if os.path.exists(src_exe):
        shutil.copy2(src_exe, dst_exe)
        print(f"  → {dst_exe}")
    else:
        print("  오류: native_host.exe를 찾을 수 없습니다.")
        return False

    return True

def register_native_host(extension_id):
    """레지스트리에 Native Host 등록"""
    print("레지스트리 등록 중...")

    # manifest.json 생성
    manifest = {
        "name": NATIVE_HOST_NAME,
        "description": "YouTube Downloader Native Host",
        "path": os.path.join(INSTALL_DIR, 'native_host.exe'),
        "type": "stdio",
        "allowed_origins": [
            f"chrome-extension://{extension_id}/"
        ]
    }

    manifest_path = os.path.join(INSTALL_DIR, f'{NATIVE_HOST_NAME}.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    # 레지스트리 등록
    try:
        key_path = f"Software\\Google\\Chrome\\NativeMessagingHosts\\{NATIVE_HOST_NAME}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, manifest_path)
        print(f"  → 레지스트리 등록 완료")
        return True
    except Exception as e:
        print(f"  오류: {e}")
        return False

def uninstall():
    """제거"""
    print("제거 중...")

    # 레지스트리 삭제
    try:
        key_path = f"Software\\Google\\Chrome\\NativeMessagingHosts\\{NATIVE_HOST_NAME}"
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        print("  → 레지스트리 삭제 완료")
    except:
        pass

    # 파일 삭제
    if os.path.exists(INSTALL_DIR):
        shutil.rmtree(INSTALL_DIR, ignore_errors=True)
        print("  → 파일 삭제 완료")

    print("\n제거 완료!")
    print("Chrome에서 확장프로그램도 수동으로 삭제해주세요.")

def main():
    print("=" * 50)
    print("     손 다운로더 설치 프로그램")
    print("=" * 50)
    print()

    # 이미 설치되어 있는지 확인
    if os.path.exists(os.path.join(INSTALL_DIR, 'native_host.exe')):
        print("이미 설치되어 있습니다.")
        print()
        print("1. 재설치")
        print("2. 제거")
        print("3. 취소")
        print()
        choice = input("선택: ").strip()

        if choice == '2':
            uninstall()
            input("\n엔터를 눌러 종료...")
            return
        elif choice != '1':
            return
        print()

    # Step 1: 파일 설치
    print("=" * 50)
    print(" STEP 1: 파일 설치")
    print("=" * 50)
    print()

    if not install_native_host():
        input("\n설치 실패. 엔터를 눌러 종료...")
        return

    if not install_extension():
        input("\n설치 실패. 엔터를 눌러 종료...")
        return

    print()

    # Step 2: Chrome에 확장프로그램 로드 안내
    print("=" * 50)
    print(" STEP 2: Chrome 확장프로그램 등록")
    print("=" * 50)
    print()
    print("Chrome에서 확장프로그램을 등록해야 합니다.")
    print()
    print("1. Chrome 주소창에 chrome://extensions 입력")
    print("2. 오른쪽 상단 '개발자 모드' 켜기")
    print("3. '압축해제된 확장 프로그램을 로드합니다' 클릭")
    print("4. 아래 경로 선택:")
    print()
    print(f"   {EXTENSION_DIR}")
    print()

    # 경로를 클립보드에 복사 시도
    try:
        import subprocess
        subprocess.run(['clip'], input=EXTENSION_DIR.encode('utf-8'), check=True)
        print("   (경로가 클립보드에 복사되었습니다!)")
        print()
    except:
        pass

    # 레지스트리에 Native Host 등록
    if not register_native_host(EXTENSION_ID):
        input("\n설치 실패. 엔터를 눌러 종료...")
        return

    print()
    print("=" * 50)
    print("     설치 완료!")
    print("=" * 50)
    print()
    print("확장프로그램 로드 후 Chrome을 재시작하세요.")
    print(f"다운로드 위치: {os.path.join(os.path.expanduser('~'), 'Videos')}")
    print()
    input("엔터를 눌러 종료...")

if __name__ == '__main__':
    main()
