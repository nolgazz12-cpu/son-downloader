"""
YouTube 다운로드 핵심 기능 모듈
yt-dlp를 사용하여 비디오/오디오 다운로드
"""
import os
import re
import yt_dlp
import urllib.request
import json
from typing import Callable, Optional, Dict, Any, List


class YouTubeDownloader:
    """YouTube 다운로드 클래스"""

    # 화질 옵션 - 더 유연한 포맷 선택 (fallback 포함)
    QUALITY_OPTIONS = {
        '최고 화질': 'bestvideo+bestaudio/best',
        '4K (2160p)': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]/best',
        '1440p': 'bestvideo[height<=1440]+bestaudio/best[height<=1440]/best',
        '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
        '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
        '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best',
        '360p': 'bestvideo[height<=360]+bestaudio/best[height<=360]/best',
    }

    # 오디오 포맷 옵션
    AUDIO_FORMATS = {
        'MP3 (320kbps)': {'format': 'bestaudio/best', 'postprocessor': 'mp3', 'quality': '320'},
        'MP3 (256kbps)': {'format': 'bestaudio/best', 'postprocessor': 'mp3', 'quality': '256'},
        'MP3 (192kbps)': {'format': 'bestaudio/best', 'postprocessor': 'mp3', 'quality': '192'},
        'MP3 (128kbps)': {'format': 'bestaudio/best', 'postprocessor': 'mp3', 'quality': '128'},
        'M4A (최고 품질)': {'format': 'bestaudio[ext=m4a]/bestaudio/best', 'postprocessor': None, 'quality': None},
        'WAV': {'format': 'bestaudio/best', 'postprocessor': 'wav', 'quality': None},
    }

    def __init__(self, output_path: str = None):
        """
        초기화

        Args:
            output_path: 다운로드 저장 경로
        """
        self.output_path = output_path or os.path.join(os.path.expanduser('~'), 'Videos')
        self.current_download = None
        self._cancelled = False

    def set_output_path(self, path: str):
        """저장 경로 설정"""
        self.output_path = path

    def cancel_download(self):
        """현재 다운로드 취소"""
        self._cancelled = True

    def get_video_info_fast(self, url: str) -> Optional[Dict[str, Any]]:
        """
        oEmbed API를 사용한 빠른 정보 가져오기 (1초 이내)
        """
        try:
            # URL에서 video ID 추출
            video_id = None
            patterns = [
                r'(?:v=|/v/|youtu\.be/|/embed/)([a-zA-Z0-9_-]{11})',
                r'shorts/([a-zA-Z0-9_-]{11})',
            ]
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    video_id = match.group(1)
                    break

            if not video_id:
                return None

            # oEmbed API 호출 (매우 빠름)
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            req = urllib.request.Request(oembed_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode('utf-8'))

            return {
                'type': 'video',
                'title': data.get('title', '제목 없음'),
                'duration': 0,  # oEmbed는 duration 제공 안함
                'thumbnail': data.get('thumbnail_url', ''),
                'channel': data.get('author_name', '알 수 없음'),
                'view_count': 0,
                'upload_date': '',
                'url': url,
            }
        except Exception as e:
            return None

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        비디오 정보 가져오기 (빠른 방법 우선 시도)

        Args:
            url: YouTube URL

        Returns:
            비디오 정보 딕셔너리
        """
        # 먼저 빠른 oEmbed 방식 시도
        fast_info = self.get_video_info_fast(url)
        if fast_info:
            return fast_info

        # 실패시 yt-dlp 방식 사용
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'skip_download': True,
            'socket_timeout': 5,
            'extract_flat': 'in_playlist',
            'no_check_certificates': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if info is None:
                    return None

                return {
                    'type': 'video',
                    'title': info.get('title', '제목 없음'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'channel': info.get('channel', info.get('uploader', '알 수 없음')),
                    'view_count': info.get('view_count', 0),
                    'upload_date': info.get('upload_date', ''),
                    'url': url,
                }

        except Exception as e:
            print(f"정보 가져오기 오류: {e}")
            return None

    def _parse_formats(self, formats: List[Dict]) -> Dict[str, List[str]]:
        """사용 가능한 포맷 파싱"""
        video_qualities = set()
        audio_formats = set()

        for f in formats:
            height = f.get('height')
            if height:
                video_qualities.add(f"{height}p")

            acodec = f.get('acodec')
            if acodec and acodec != 'none':
                audio_formats.add(f.get('ext', 'unknown'))

        return {
            'video': sorted(list(video_qualities), key=lambda x: int(x[:-1]), reverse=True),
            'audio': list(audio_formats),
        }

    def download_video(
        self,
        url: str,
        quality: str = '최고 화질',
        progress_callback: Callable[[Dict], None] = None,
        complete_callback: Callable[[bool, str], None] = None,
    ) -> bool:
        """
        비디오 다운로드

        Args:
            url: YouTube URL
            quality: 화질 옵션 키
            progress_callback: 진행률 콜백 (percent, speed, eta, filename)
            complete_callback: 완료 콜백 (success, message)

        Returns:
            성공 여부
        """
        self._cancelled = False
        format_string = self.QUALITY_OPTIONS.get(quality, self.QUALITY_OPTIONS['최고 화질'])

        def progress_hook(d):
            if self._cancelled:
                raise Exception("다운로드 취소됨")

            if progress_callback:
                if d['status'] == 'downloading':
                    progress_callback({
                        'status': 'downloading',
                        'percent': d.get('_percent_str', '0%').strip(),
                        'speed': d.get('_speed_str', 'N/A').strip(),
                        'eta': d.get('_eta_str', 'N/A').strip(),
                        'filename': os.path.basename(d.get('filename', '')),
                        'downloaded': d.get('downloaded_bytes', 0),
                        'total': d.get('total_bytes', d.get('total_bytes_estimate', 0)),
                    })
                elif d['status'] == 'finished':
                    progress_callback({
                        'status': 'finished',
                        'filename': os.path.basename(d.get('filename', '')),
                    })

        ydl_opts = {
            'format': format_string,
            'outtmpl': os.path.join(self.output_path, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,  # 단일 영상만 다운로드
            'retries': 10,
            'fragment_retries': 10,
            'skip_unavailable_fragments': True,  # 없는 fragment 건너뛰기
            'ignoreerrors': True,
            'extractor_retries': 3,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            if complete_callback:
                complete_callback(True, "다운로드 완료")
            return True

        except Exception as e:
            error_msg = str(e)
            if complete_callback:
                complete_callback(False, error_msg)
            return False

    def download_audio(
        self,
        url: str,
        audio_format: str = 'MP3 (320kbps)',
        progress_callback: Callable[[Dict], None] = None,
        complete_callback: Callable[[bool, str], None] = None,
    ) -> bool:
        """
        오디오만 다운로드

        Args:
            url: YouTube URL
            audio_format: 오디오 포맷 옵션 키
            progress_callback: 진행률 콜백
            complete_callback: 완료 콜백

        Returns:
            성공 여부
        """
        self._cancelled = False
        format_info = self.AUDIO_FORMATS.get(audio_format, self.AUDIO_FORMATS['MP3 (320kbps)'])

        def progress_hook(d):
            if self._cancelled:
                raise Exception("다운로드 취소됨")

            if progress_callback:
                if d['status'] == 'downloading':
                    progress_callback({
                        'status': 'downloading',
                        'percent': d.get('_percent_str', '0%').strip(),
                        'speed': d.get('_speed_str', 'N/A').strip(),
                        'eta': d.get('_eta_str', 'N/A').strip(),
                        'filename': os.path.basename(d.get('filename', '')),
                        'downloaded': d.get('downloaded_bytes', 0),
                        'total': d.get('total_bytes', d.get('total_bytes_estimate', 0)),
                    })
                elif d['status'] == 'finished':
                    progress_callback({
                        'status': 'processing',
                        'filename': os.path.basename(d.get('filename', '')),
                    })

        ydl_opts = {
            'format': format_info['format'],
            'outtmpl': os.path.join(self.output_path, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,  # 단일 영상만 다운로드
        }

        # 후처리기 설정 (MP3, WAV 변환)
        if format_info['postprocessor']:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': format_info['postprocessor'],
            }]
            if format_info['quality']:
                ydl_opts['postprocessors'][0]['preferredquality'] = format_info['quality']

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            if complete_callback:
                complete_callback(True, "다운로드 완료")
            return True

        except Exception as e:
            error_msg = str(e)
            if complete_callback:
                complete_callback(False, error_msg)
            return False

    def download_playlist(
        self,
        url: str,
        download_type: str = 'video',  # 'video' or 'audio'
        quality: str = '최고 화질',
        audio_format: str = 'MP3 (320kbps)',
        progress_callback: Callable[[Dict], None] = None,
        item_callback: Callable[[int, int, str], None] = None,
        complete_callback: Callable[[bool, str], None] = None,
    ) -> bool:
        """
        플레이리스트 다운로드

        Args:
            url: 플레이리스트 URL
            download_type: 'video' 또는 'audio'
            quality: 비디오 화질
            audio_format: 오디오 포맷
            progress_callback: 진행률 콜백
            item_callback: 항목별 콜백 (current, total, title)
            complete_callback: 완료 콜백
        """
        self._cancelled = False

        # 플레이리스트 정보 가져오기
        info = self.get_video_info(url)
        if not info or info['type'] != 'playlist':
            if complete_callback:
                complete_callback(False, "플레이리스트를 찾을 수 없습니다")
            return False

        entries = info['entries']
        total = len(entries)

        for idx, entry in enumerate(entries, 1):
            if self._cancelled:
                if complete_callback:
                    complete_callback(False, "다운로드 취소됨")
                return False

            video_url = entry.get('url') or entry.get('webpage_url')
            if not video_url:
                continue

            title = entry.get('title', f'항목 {idx}')

            if item_callback:
                item_callback(idx, total, title)

            if download_type == 'video':
                self.download_video(video_url, quality, progress_callback)
            else:
                self.download_audio(video_url, audio_format, progress_callback)

        if complete_callback:
            complete_callback(True, f"플레이리스트 다운로드 완료 ({total}개)")
        return True


def format_duration(seconds: int) -> str:
    """초를 시:분:초 형식으로 변환"""
    if not seconds:
        return "00:00"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_filesize(bytes_size: int) -> str:
    """바이트를 읽기 쉬운 크기로 변환"""
    if not bytes_size:
        return "0 B"

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(bytes_size)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.1f} {units[unit_index]}"


def is_valid_youtube_url(url: str) -> bool:
    """YouTube URL 유효성 검사"""
    youtube_patterns = [
        r'^(https?://)?(www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^(https?://)?(www\.)?youtube\.com/playlist\?list=[\w-]+',
        r'^(https?://)?(www\.)?youtu\.be/[\w-]+',
        r'^(https?://)?(www\.)?youtube\.com/shorts/[\w-]+',
    ]

    for pattern in youtube_patterns:
        if re.match(pattern, url):
            return True
    return False
