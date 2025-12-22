"""
YouTube Downloader - 메인 GUI 애플리케이션
4K Video Downloader 스타일의 YouTube 다운로드 프로그램
"""
import sys
import os
import json
import webbrowser
import time
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QComboBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QTabBar, QFrame, QMessageBox, QMenu, QStyle, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QSettings
from PyQt6.QtGui import QFont, QAction, QIcon, QClipboard, QColor

# 쿠팡 파트너스 설정
COUPANG_LINK = 'https://link.coupang.com/a/dgLA94'
COUPANG_COOKIE_HOURS = 20

# 설정 파일 경로
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')

from downloader import (
    YouTubeDownloader, format_duration, format_filesize, is_valid_youtube_url
)


class DownloadThread(QThread):
    """다운로드 작업 스레드"""
    progress = pyqtSignal(dict)
    finished = pyqtSignal(bool, str)
    info_fetched = pyqtSignal(dict)

    def __init__(self, downloader: YouTubeDownloader, url: str, download_type: str,
                 quality: str = None, audio_format: str = None):
        super().__init__()
        self.downloader = downloader
        self.url = url
        self.download_type = download_type  # 'video', 'audio', 'info'
        self.quality = quality
        self.audio_format = audio_format

    def run(self):
        if self.download_type == 'info':
            try:
                info = self.downloader.get_video_info(self.url)
                if info:
                    self.info_fetched.emit(info)
                else:
                    self.finished.emit(False, "정보를 가져올 수 없습니다")
            except Exception as e:
                self.finished.emit(False, str(e))
        elif self.download_type == 'video':
            self.downloader.download_video(
                self.url,
                self.quality,
                progress_callback=self.progress.emit,
                complete_callback=self.finished.emit
            )
        elif self.download_type == 'audio':
            self.downloader.download_audio(
                self.url,
                self.audio_format,
                progress_callback=self.progress.emit,
                complete_callback=self.finished.emit
            )


class DownloadItem:
    """다운로드 항목 데이터"""
    def __init__(self, url: str, title: str, duration: str, channel: str):
        self.url = url
        self.title = title
        self.duration = duration
        self.channel = channel
        self.progress = 0
        self.status = "대기중"
        self.speed = ""
        self.eta = ""
        self.file_size = ""
        self.download_type = "video"
        self.quality = "최고 화질"
        self.audio_format = "MP3 (320kbps)"


class MainWindow(QMainWindow):
    """메인 윈도우"""

    def __init__(self):
        super().__init__()
        self.downloader = YouTubeDownloader()
        self.download_items = []
        self.current_download_thread = None
        self.is_downloading = False
        self.last_coupang_click = 0  # 쿠팡 클릭 시간 기록

        # 저장된 설정 불러오기
        self.load_settings()

        self.init_ui()
        self.setup_connections()

    def should_open_coupang(self):
        """쿠팡 링크 열어야 하는지 확인 (20시간 내 클릭 안했으면 True)"""
        current_time = time.time()
        hours_passed = (current_time - self.last_coupang_click) / 3600
        return hours_passed >= COUPANG_COOKIE_HOURS

    def open_coupang(self):
        """쿠팡 파트너스 링크 열기"""
        if self.should_open_coupang():
            webbrowser.open(COUPANG_LINK)
            self.last_coupang_click = time.time()
            self.save_settings()

    def load_settings(self):
        """설정 불러오기"""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    saved_path = settings.get('output_path', '')
                    if saved_path and os.path.exists(saved_path):
                        self.downloader.set_output_path(saved_path)
                    self.last_coupang_click = settings.get('last_coupang_click', 0)
            except:
                pass

    def save_settings(self):
        """설정 저장"""
        settings = {
            'output_path': self.downloader.output_path,
            'last_coupang_click': self.last_coupang_click
        }
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except:
            pass

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("YouTube Downloader")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)

        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 상단 툴바 영역
        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border-bottom: 1px solid #ddd;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(10)

        # 링크 붙여넣기 버튼
        self.paste_btn = QPushButton("📋 링크 붙여넣기")
        self.paste_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        toolbar_layout.addWidget(self.paste_btn)

        # URL 입력 필드
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("YouTube 링크를 입력하거나 붙여넣기 버튼을 클릭하세요...")
        self.url_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
            }
        """)
        toolbar_layout.addWidget(self.url_input, 1)

        # 다운로드 타입 선택
        type_label = QLabel("다운로드:")
        type_label.setStyleSheet("border: none; font-size: 13px;")
        toolbar_layout.addWidget(type_label)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["비디오", "오디오"])
        self.type_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 15px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 13px;
                min-width: 80px;
            }
            QComboBox:hover {
                border-color: #4CAF50;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
        """)
        toolbar_layout.addWidget(self.type_combo)

        # 화질/품질 선택
        quality_label = QLabel("화질:")
        quality_label.setStyleSheet("border: none; font-size: 13px;")
        toolbar_layout.addWidget(quality_label)

        self.quality_combo = QComboBox()
        self.update_quality_options()
        self.quality_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 15px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 13px;
                min-width: 120px;
            }
            QComboBox:hover {
                border-color: #4CAF50;
            }
        """)
        toolbar_layout.addWidget(self.quality_combo)

        # 다운로드 시작 버튼
        self.download_btn = QPushButton("▶ 다운로드")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
            QPushButton:pressed {
                background-color: #D84315;
            }
        """)
        toolbar_layout.addWidget(self.download_btn)

        # 저장 경로 버튼
        self.path_btn = QPushButton("📁 저장 위치")
        self.path_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 15px;
                font-size: 13px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        toolbar_layout.addWidget(self.path_btn)

        main_layout.addWidget(toolbar_widget)

        # 탭 바 영역
        tab_widget = QWidget()
        tab_widget.setStyleSheet("background-color: white; border-bottom: 1px solid #ddd;")
        tab_layout = QHBoxLayout(tab_widget)
        tab_layout.setContentsMargins(10, 5, 10, 5)

        self.tab_all = QPushButton("전체")
        self.tab_video = QPushButton("동영상")
        self.tab_audio = QPushButton("오디오")

        tab_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 8px 15px;
                font-size: 13px;
                color: #666;
            }
            QPushButton:hover {
                color: #333;
            }
            QPushButton:checked {
                color: #4CAF50;
                font-weight: bold;
                border-bottom: 2px solid #4CAF50;
            }
        """
        for btn in [self.tab_all, self.tab_video, self.tab_audio]:
            btn.setCheckable(True)
            btn.setStyleSheet(tab_style)

        self.tab_all.setChecked(True)

        tab_layout.addWidget(self.tab_all)
        tab_layout.addWidget(self.tab_video)
        tab_layout.addWidget(self.tab_audio)
        tab_layout.addStretch()

        # 항목 수 표시
        self.item_count_label = QLabel("0 아이템")
        self.item_count_label.setStyleSheet("color: #999; font-size: 12px;")
        tab_layout.addWidget(self.item_count_label)

        main_layout.addWidget(tab_widget)

        # 다운로드 목록 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["", "제목", "길이", "상태", "진행률", "속도"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 100)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                border: none;
                gridline-color: #eee;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 10px;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
            QHeaderView::section {
                background-color: #fafafa;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #ddd;
                font-weight: bold;
            }
        """)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        main_layout.addWidget(self.table)

        # 하단 상태바 영역
        status_widget = QWidget()
        status_widget.setStyleSheet("background-color: #fafafa; border-top: 1px solid #ddd;")
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(15, 10, 15, 10)

        self.status_label = QLabel("준비됨")
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        # 저장 경로 표시
        self.path_label = QLabel(f"저장 위치: {self.downloader.output_path}")
        self.path_label.setStyleSheet("color: #999; font-size: 12px;")
        status_layout.addWidget(self.path_label)

        main_layout.addWidget(status_widget)

        # 메뉴바
        self.create_menu()

    def create_menu(self):
        """메뉴바 생성"""
        menubar = self.menuBar()

        # 파일 메뉴
        file_menu = menubar.addMenu("파일")

        paste_action = QAction("링크 붙여넣기", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.paste_url)
        file_menu.addAction(paste_action)

        file_menu.addSeparator()

        change_path_action = QAction("저장 위치 변경", self)
        change_path_action.triggered.connect(self.change_save_path)
        file_menu.addAction(change_path_action)

        open_folder_action = QAction("저장 폴더 열기", self)
        open_folder_action.triggered.connect(self.open_save_folder)
        file_menu.addAction(open_folder_action)

        file_menu.addSeparator()

        exit_action = QAction("종료", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 편집 메뉴
        edit_menu = menubar.addMenu("편집")

        select_all_action = QAction("전체 선택", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.table.selectAll)
        edit_menu.addAction(select_all_action)

        delete_action = QAction("선택 항목 삭제", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self.delete_selected)
        edit_menu.addAction(delete_action)

        clear_action = QAction("완료 항목 지우기", self)
        clear_action.triggered.connect(self.clear_completed)
        edit_menu.addAction(clear_action)

        # 다운로드 메뉴
        download_menu = menubar.addMenu("다운로드")

        start_action = QAction("다운로드 시작", self)
        start_action.triggered.connect(self.start_all_downloads)
        download_menu.addAction(start_action)

        stop_action = QAction("다운로드 중지", self)
        stop_action.triggered.connect(self.stop_download)
        download_menu.addAction(stop_action)

        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")

        about_action = QAction("프로그램 정보", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_connections(self):
        """시그널 연결"""
        self.paste_btn.clicked.connect(self.paste_url)
        self.url_input.returnPressed.connect(self.add_url)
        self.type_combo.currentIndexChanged.connect(self.update_quality_options)
        self.download_btn.clicked.connect(self.on_download_btn_clicked)
        self.path_btn.clicked.connect(self.change_save_path)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        # 탭 버튼
        self.tab_all.clicked.connect(lambda: self.filter_table("all"))
        self.tab_video.clicked.connect(lambda: self.filter_table("video"))
        self.tab_audio.clicked.connect(lambda: self.filter_table("audio"))

    def on_download_btn_clicked(self):
        """다운로드 버튼 클릭 핸들러"""
        self.start_all_downloads()

    def update_quality_options(self):
        """다운로드 타입에 따라 화질/품질 옵션 업데이트"""
        self.quality_combo.clear()
        if self.type_combo.currentText() == "비디오":
            self.quality_combo.addItems(list(YouTubeDownloader.QUALITY_OPTIONS.keys()))
        else:
            self.quality_combo.addItems(list(YouTubeDownloader.AUDIO_FORMATS.keys()))

    def paste_url(self):
        """클립보드에서 URL 붙여넣기"""
        clipboard = QApplication.clipboard()
        url = clipboard.text().strip()

        if url:
            self.url_input.setText(url)
            self.add_url()

    def add_url(self):
        """URL 추가 및 정보 가져오기"""
        url = self.url_input.text().strip()

        if not url:
            return

        # shorts URL을 일반 형식으로 변환
        if '/shorts/' in url:
            url = url.replace('/shorts/', '/watch?v=')

        if not is_valid_youtube_url(url):
            QMessageBox.warning(self, "오류", "올바른 YouTube URL이 아닙니다.")
            return

        # 중복 체크
        for item in self.download_items:
            if item.url == url:
                QMessageBox.information(self, "알림", "이미 추가된 URL입니다.")
                return

        # 먼저 리스트에 추가 (서버 연결중 상태로)
        item = DownloadItem(
            url=url,
            title="정보 가져오는 중...",
            duration="--:--",
            channel=""
        )
        item.status = "서버 연결중"
        self.add_item_to_table(item)
        self.url_input.clear()
        self.update_item_count()

        # 정보 가져오기 스레드 시작
        current_row = len(self.download_items) - 1
        info_thread = DownloadThread(self.downloader, url, 'info')
        info_thread.info_fetched.connect(lambda info, r=current_row: self.on_info_fetched(info, r))
        info_thread.finished.connect(lambda s, m, r=current_row: self.on_info_error(s, m, r))
        info_thread.start()

        # 스레드 참조 유지 (가비지 컬렉션 방지)
        if not hasattr(self, 'info_threads'):
            self.info_threads = []
        self.info_threads.append(info_thread)

    def on_info_fetched(self, info: dict, row: int):
        """비디오 정보 수신 후 바로 다운로드 시작"""
        if row >= len(self.download_items):
            return

        item = self.download_items[row]
        item.title = info['title']
        item.duration = format_duration(info.get('duration', 0))
        item.channel = info.get('channel', '')
        item.status = "대기중"

        # 테이블 업데이트
        self.table.item(row, 1).setText(item.title)
        self.table.item(row, 1).setToolTip(f"{item.title}\n채널: {item.channel}\nURL: {item.url}")
        self.table.item(row, 2).setText(item.duration)
        self.table.item(row, 3).setText(item.status)

        self.status_label.setText("준비됨")

        # 쿠팡 파트너스 링크 열기 (20시간 내 클릭 안했으면)
        self.open_coupang()

        # 바로 다운로드 시작
        self.start_all_downloads()

    def on_info_error(self, success: bool, message: str, row: int):
        """정보 가져오기 에러 - 그래도 다운로드 시도 가능"""
        if not success and row < len(self.download_items):
            item = self.download_items[row]
            # 정보 가져오기 실패해도 다운로드는 시도 가능
            item.status = "대기중"
            item.title = "제목 없음 (다운로드 시도 가능)"
            self.table.item(row, 1).setText(item.title)
            self.table.item(row, 3).setText(item.status)
            self.status_label.setText("준비됨")

    def add_item_to_table(self, item: DownloadItem):
        """테이블에 항목 추가"""
        item.download_type = "video" if self.type_combo.currentText() == "비디오" else "audio"
        item.quality = self.quality_combo.currentText()

        self.download_items.append(item)
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 체크박스 대용 아이콘
        type_icon = "🎬" if item.download_type == "video" else "🎵"
        self.table.setItem(row, 0, QTableWidgetItem(type_icon))
        self.table.item(row, 0).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # 제목
        title_item = QTableWidgetItem(item.title)
        title_item.setToolTip(f"{item.title}\n채널: {item.channel}\nURL: {item.url}")
        self.table.setItem(row, 1, title_item)

        # 길이
        self.table.setItem(row, 2, QTableWidgetItem(item.duration))
        self.table.item(row, 2).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # 상태
        self.table.setItem(row, 3, QTableWidgetItem(item.status))
        self.table.item(row, 3).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # 진행률
        progress_item = QTableWidgetItem("0%")
        progress_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 4, progress_item)

        # 속도
        self.table.setItem(row, 5, QTableWidgetItem(""))
        self.table.item(row, 5).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def update_item_count(self):
        """항목 수 업데이트"""
        self.item_count_label.setText(f"{len(self.download_items)} 아이템")

    def filter_table(self, filter_type: str):
        """테이블 필터링"""
        # 버튼 상태 업데이트
        self.tab_all.setChecked(filter_type == "all")
        self.tab_video.setChecked(filter_type == "video")
        self.tab_audio.setChecked(filter_type == "audio")

        for row in range(self.table.rowCount()):
            if filter_type == "all":
                self.table.setRowHidden(row, False)
            else:
                item = self.download_items[row]
                self.table.setRowHidden(row, item.download_type != filter_type)

    def show_context_menu(self, pos):
        """컨텍스트 메뉴"""
        menu = QMenu(self)

        start_action = menu.addAction("다운로드 시작")
        start_action.triggered.connect(self.start_selected_download)

        menu.addSeparator()

        delete_action = menu.addAction("삭제")
        delete_action.triggered.connect(self.delete_selected)

        copy_url_action = menu.addAction("URL 복사")
        copy_url_action.triggered.connect(self.copy_selected_url)

        menu.exec(self.table.mapToGlobal(pos))

    def start_all_downloads(self):
        """모든 대기 항목 다운로드 시작"""
        if self.is_downloading:
            self.status_label.setText("이미 다운로드 중입니다")
            return

        has_pending = any(item.status == "대기중" for item in self.download_items)
        if not has_pending:
            self.status_label.setText("다운로드할 항목이 없습니다")
            return

        self.status_label.setText("다운로드 시작...")
        self.process_next_download()

    def process_next_download(self):
        """다음 다운로드 처리"""
        # 대기 중인 항목 찾기
        for idx, item in enumerate(self.download_items):
            if item.status == "대기중":
                self.start_download(idx)
                return

        # 모든 다운로드 완료
        self.is_downloading = False
        self.status_label.setText("모든 다운로드 완료")

    def start_download(self, index: int):
        """특정 항목 다운로드 시작"""
        if index >= len(self.download_items):
            return

        item = self.download_items[index]
        item.status = "다운로드 중"
        self.update_table_item(index)

        self.is_downloading = True
        self.current_download_index = index
        self.status_label.setText(f"다운로드 중: {item.title}")

        download_type = item.download_type
        quality = item.quality if download_type == "video" else None
        audio_format = item.quality if download_type == "audio" else None

        self.current_download_thread = DownloadThread(
            self.downloader, item.url, download_type, quality, audio_format
        )
        self.current_download_thread.progress.connect(
            lambda p: self.on_download_progress(index, p)
        )
        self.current_download_thread.finished.connect(
            lambda s, m: self.on_download_finished(index, s, m)
        )
        self.current_download_thread.start()

    def start_selected_download(self):
        """선택된 항목 다운로드 시작"""
        rows = set(idx.row() for idx in self.table.selectedIndexes())
        for row in rows:
            if self.download_items[row].status == "대기중":
                self.start_download(row)
                break

    def on_download_progress(self, index: int, progress: dict):
        """다운로드 진행률 업데이트"""
        if index >= len(self.download_items):
            return

        item = self.download_items[index]

        if progress['status'] == 'downloading':
            item.progress = progress.get('percent', '0%')
            item.speed = progress.get('speed', '')
            item.eta = progress.get('eta', '')
            item.status = "다운로드 중"
        elif progress['status'] == 'processing':
            item.status = "변환 중"
            item.progress = "100%"
        elif progress['status'] == 'finished':
            item.status = "완료"
            item.progress = "100%"

        self.update_table_item(index)

    def on_download_finished(self, index: int, success: bool, message: str):
        """다운로드 완료"""
        if index >= len(self.download_items):
            return

        item = self.download_items[index]

        if success:
            item.status = "✓ 완료"
            item.progress = "100%"
        else:
            item.status = "✗ 실패"
            if "취소" in message:
                item.status = "취소됨"

        item.speed = ""
        self.update_table_item(index)

        # 다음 다운로드 처리
        QTimer.singleShot(500, self.process_next_download)

    def update_table_item(self, index: int):
        """테이블 항목 업데이트"""
        if index >= len(self.download_items):
            return

        item = self.download_items[index]

        self.table.item(index, 3).setText(item.status)
        self.table.item(index, 4).setText(str(item.progress))
        self.table.item(index, 5).setText(item.speed)

        # 상태에 따른 색상
        if "완료" in item.status:
            color = QColor("#4CAF50")
        elif "실패" in item.status:
            color = QColor("#f44336")
        elif "다운로드 중" in item.status or "변환 중" in item.status:
            color = QColor("#2196F3")
        else:
            color = QColor("#666")

        self.table.item(index, 3).setForeground(color)

    def stop_download(self):
        """다운로드 중지"""
        self.downloader.cancel_download()
        self.is_downloading = False
        self.status_label.setText("다운로드 중지됨")

    def delete_selected(self):
        """선택된 항목 삭제"""
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()), reverse=True)
        for row in rows:
            if row < len(self.download_items):
                del self.download_items[row]
                self.table.removeRow(row)
        self.update_item_count()

    def clear_completed(self):
        """완료된 항목 삭제"""
        rows_to_delete = []
        for idx, item in enumerate(self.download_items):
            if "완료" in item.status:
                rows_to_delete.append(idx)

        for row in reversed(rows_to_delete):
            del self.download_items[row]
            self.table.removeRow(row)

        self.update_item_count()

    def copy_selected_url(self):
        """선택된 항목 URL 복사"""
        rows = list(set(idx.row() for idx in self.table.selectedIndexes()))
        if rows:
            url = self.download_items[rows[0]].url
            QApplication.clipboard().setText(url)

    def change_save_path(self):
        """저장 경로 변경"""
        path = QFileDialog.getExistingDirectory(
            self, "저장 위치 선택", self.downloader.output_path
        )
        if path:
            self.downloader.set_output_path(path)
            self.path_label.setText(f"저장 위치: {path}")
            self.save_settings()  # 설정 저장

    def open_save_folder(self):
        """저장 폴더 열기"""
        os.startfile(self.downloader.output_path)

    def show_about(self):
        """프로그램 정보"""
        QMessageBox.about(
            self, "프로그램 정보",
            "YouTube Downloader\n\n"
            "YouTube 영상 및 음악을 다운로드하는 프로그램입니다.\n\n"
            "지원 기능:\n"
            "• 비디오 다운로드 (최대 4K)\n"
            "• 오디오 추출 (MP3, M4A, WAV)\n"
            "• 플레이리스트 다운로드\n"
            "• 다양한 화질/품질 선택"
        )


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 앱 폰트 설정
    font = QFont("맑은 고딕", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
