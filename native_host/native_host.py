#!/usr/bin/env python3
"""
YouTube Downloader Native Messaging Host
Chrome 확장프로그램과 통신하여 yt-dlp로 다운로드 수행
"""
import sys
import os
import threading

# 로그 파일 - 가장 먼저 설정
LOG_FILE = os.path.join(os.path.expanduser('~'), 'son_downloader_log.txt')

def log(msg):
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{msg}\n")
    except:
        pass

# 시작 로그
log("=" * 50)
log("Native host starting...")

import json
import struct
import traceback
import subprocess

log("Imports done")

try:
    # Windows에서 stdin/stdout을 바이너리 모드로 설정
    if sys.platform == 'win32':
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        log("Binary mode set")
except Exception as e:
    log(f"Init error: {e}")

log("Loading yt_dlp...")
import yt_dlp
log("yt_dlp loaded")


# 기본 다운로드 경로 (사용자 Videos 폴더)
DEFAULT_DOWNLOAD_PATH = os.path.join(os.path.expanduser('~'), 'Videos')

def get_message():
    """확장프로그램에서 메시지 읽기"""
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack('=I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode('utf-8')
    return json.loads(message)

def send_message(message, msg_id=None):
    """확장프로그램에 메시지 보내기"""
    if msg_id is not None:
        message['_id'] = msg_id
    encoded = json.dumps(message, ensure_ascii=False).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('=I', len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()

def get_download_url(url, quality='best', format_type='video'):
    """yt-dlp로 다운로드 URL 추출"""
    if format_type == 'audio':
        format_string = 'bestaudio/best'
    elif quality == '720':
        format_string = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
    else:
        format_string = 'bestvideo+bestaudio/best'

    ydl_opts = {
        'format': format_string,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'skip_download': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if info is None:
                return None

            download_url = info.get('url')

            if not download_url and 'requested_formats' in info:
                for fmt in info['requested_formats']:
                    if format_type == 'audio':
                        if fmt.get('acodec') != 'none':
                            download_url = fmt.get('url')
                            break
                    else:
                        if fmt.get('vcodec') != 'none':
                            download_url = fmt.get('url')
                            break

            return {
                'url': download_url,
                'title': info.get('title', 'video'),
                'ext': info.get('ext', 'mp4')
            }
    except Exception as e:
        return {'error': str(e)}

def download_video(url, quality='best', format_type='video'):
    """yt-dlp로 직접 다운로드"""
    if format_type == 'audio':
        format_string = 'bestaudio/best'
        postprocessors = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }]
    else:
        if quality == '720':
            format_string = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
        else:
            format_string = 'bestvideo+bestaudio/best'
        postprocessors = []

    ydl_opts = {
        'format': format_string,
        'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }

    if postprocessors:
        ydl_opts['postprocessors'] = postprocessors

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return {
                'success': True,
                'title': info.get('title', 'video'),
                'path': DOWNLOAD_PATH
            }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def main():
    log("Native host started")
    try:
        while True:
            message = get_message()
            log(f"Received: {message}")
            if message is None:
                break

            action = message.get('action')
            url = message.get('url')
            quality = message.get('quality', 'best')
            format_type = message.get('format', 'video')
            msg_id = message.get('_id')  # 메시지 ID 추출

            if action == 'ping':
                send_message({'status': 'ok', 'version': '1.0.0'}, msg_id)

            elif action == 'getPath':
                # 기본 다운로드 경로 반환
                send_message({'path': DEFAULT_DOWNLOAD_PATH}, msg_id)

            elif action == 'selectPath':
                # PowerShell로 폴더 선택 다이얼로그 (경로 입력 가능한 버전)
                try:
                    ps_script = '''
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = "다운로드 폴더 선택 (폴더 선택 후 열기 클릭)"
$dialog.InitialDirectory = "{}"
$dialog.ValidateNames = $false
$dialog.CheckFileExists = $false
$dialog.CheckPathExists = $true
$dialog.FileName = "폴더 선택"
$result = $dialog.ShowDialog()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {{
    Write-Output (Split-Path $dialog.FileName)
}}
'''.format(DEFAULT_DOWNLOAD_PATH.replace('\\', '\\\\'))

                    result = subprocess.run(
                        ['powershell', '-WindowStyle', 'Hidden', '-Command', ps_script],
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    folder = result.stdout.strip()
                    if folder:
                        send_message({'path': folder}, msg_id)
                    else:
                        send_message({'path': None, 'cancelled': True}, msg_id)
                except Exception as e:
                    log(f"Folder dialog error: {e}")
                    send_message({'error': str(e)}, msg_id)

            elif action == 'getProgress':
                # 진행률 파일에서 상태 읽기
                progress_file = os.path.join(os.path.expanduser('~'), 'son_downloader_progress.json')
                try:
                    if os.path.exists(progress_file):
                        with open(progress_file, 'r', encoding='utf-8') as f:
                            progress_data = json.load(f)
                        send_message(progress_data, msg_id)
                    else:
                        send_message({'status': 'waiting'}, msg_id)
                except Exception as e:
                    send_message({'status': 'error', 'error': str(e)}, msg_id)

            elif action == 'getUrl':
                result = get_download_url(url, quality, format_type)
                send_message(result, msg_id)

            elif action == 'download':
                log(f"Starting download: {url}")
                # 커스텀 다운로드 경로 (없으면 기본 경로)
                custom_path = message.get('downloadPath', '') or DEFAULT_DOWNLOAD_PATH

                # 진행률 파일 경로
                progress_file = os.path.join(os.path.expanduser('~'), 'son_downloader_progress.json')

                # 백그라운드 스레드에서 다운로드 실행
                def do_download(video_url, download_path, fmt_type, qual):
                    def save_progress(status, percent=0, title='', error=''):
                        try:
                            with open(progress_file, 'w', encoding='utf-8') as f:
                                json.dump({
                                    'status': status,
                                    'percent': percent,
                                    'title': title,
                                    'error': error,
                                    'path': download_path
                                }, f, ensure_ascii=False)
                        except:
                            pass

                    def progress_hook(d):
                        if d['status'] == 'downloading':
                            percent = 0
                            if d.get('total_bytes'):
                                percent = int(d['downloaded_bytes'] / d['total_bytes'] * 100)
                            elif d.get('total_bytes_estimate'):
                                percent = int(d['downloaded_bytes'] / d['total_bytes_estimate'] * 100)
                            save_progress('downloading', percent, d.get('filename', ''))
                        elif d['status'] == 'finished':
                            save_progress('merging', 99, d.get('filename', ''))

                    try:
                        log(f"[DL] Thread started for {video_url}")
                        save_progress('starting', 0)

                        # stdout/stderr를 devnull로 리다이렉트하여 minicurses 에러 방지
                        import io
                        sys.stdout = io.StringIO()
                        sys.stderr = io.StringIO()

                        if fmt_type == 'audio':
                            format_string = 'bestaudio/best'
                            postprocessors = [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'mp3',
                                'preferredquality': '320',
                            }]
                        else:
                            if qual == '720':
                                format_string = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
                            else:
                                format_string = 'bestvideo+bestaudio/best'
                            postprocessors = []

                        # stdout/stderr를 완전히 차단하여 yt-dlp 출력 에러 방지
                        ydl_opts = {
                            'format': format_string,
                            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                            'quiet': True,
                            'no_warnings': True,
                            'noplaylist': True,
                            'noprogress': True,
                            'no_color': True,
                            'progress_hooks': [progress_hook],
                            'merge_output_format': 'mp4',  # webm을 mp4로 변환
                            'logger': type('NullLogger', (), {
                                'debug': lambda self, msg: None,
                                'warning': lambda self, msg: None,
                                'error': lambda self, msg: log(f"[YT-DLP ERROR] {msg}"),
                            })(),
                        }
                        if postprocessors:
                            ydl_opts['postprocessors'] = postprocessors

                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(video_url, download=True)
                            title = info.get('title', 'video')
                            save_progress('complete', 100, title)
                            log(f"[DL] Download complete: {title} -> {download_path}")
                    except Exception as e:
                        save_progress('error', 0, '', str(e))
                        log(f"[DL] Download error: {e}\n{traceback.format_exc()}")

                # 스레드 시작 (daemon=False로 native host 종료 후에도 계속 실행)
                t = threading.Thread(target=do_download, args=(url, custom_path, format_type, quality), daemon=False)
                t.start()

                # 즉시 응답 반환
                send_message({'success': True, 'message': '다운로드 시작됨', 'path': custom_path}, msg_id)

            else:
                send_message({'error': 'Unknown action'}, msg_id)
    except Exception as e:
        log(f"Main error: {e}\n{traceback.format_exc()}")
        send_message({'success': False, 'error': str(e)})

if __name__ == '__main__':
    main()
