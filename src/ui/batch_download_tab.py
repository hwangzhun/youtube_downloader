"""
批量下载标签页模块
提供解析多条视频信息并选择质量的界面
"""

import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTextEdit, QPushButton,
    QMessageBox, QTableWidget, QTableWidgetItem, QComboBox, QLabel, QStatusBar,
    QLineEdit, QProgressBar, QFileDialog, QRadioButton
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from src.core.video_info.video_info_parser import VideoInfoParser
from src.core.downloader import VideoDownloader
from src.core.cookie_manager import CookieManager
from src.utils.logger import LoggerManager
from src.utils.config import ConfigManager


class BatchDownloadTab(QWidget):
    """批量下载标签页类"""

    def __init__(self, config_manager: ConfigManager, status_bar: QStatusBar = None):
        super().__init__()

        self.logger = LoggerManager().get_logger()
        self.config_manager = config_manager
        self.status_bar = status_bar

        self.video_info_parser = VideoInfoParser()
        self.downloader = VideoDownloader()
        self.cookie_manager = CookieManager()

        self.is_downloading = False
        self.download_thread = None

        self.init_ui()
        self.set_default_download_dir()

    class BatchParseThread(QThread):
        """批量解析线程"""
        video_parsed = pyqtSignal(int, dict, list)
        progress_updated = pyqtSignal(str)
        parse_finished = pyqtSignal()

        def __init__(self, parser: VideoInfoParser, urls: list):
            super().__init__()
            self.parser = parser
            self.urls = urls

        def run(self):
            for index, url in enumerate(self.urls, start=1):
                try:
                    self.progress_updated.emit(f"正在解析第 {index} 个视频...")
                    info = self.parser.parse_video(url)
                    basic = self.parser.get_basic_info(info)
                    fmts = self.parser.get_available_formats(info)
                    formatted = self.parser.get_formatted_formats(fmts)
                    self.video_parsed.emit(index, basic, formatted)
                except Exception as e:
                    self.video_parsed.emit(index, {'error': str(e)}, [])
            self.progress_updated.emit("解析完成")
            self.parse_finished.emit()

    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 输入区域
        input_group = QGroupBox("视频链接")
        input_layout = QVBoxLayout(input_group)

        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("每行输入一个视频链接")
        input_layout.addWidget(self.url_input)

        parse_layout = QHBoxLayout()
        self.parse_button = QPushButton("解析视频信息")
        self.parse_button.clicked.connect(self.parse_video_infos)
        parse_layout.addStretch()
        parse_layout.addWidget(self.parse_button)
        input_layout.addLayout(parse_layout)

        main_layout.addWidget(input_group)

        # 表格区域
        table_group = QGroupBox("视频列表")
        table_layout = QVBoxLayout(table_group)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["序号", "标题", "时长", "视频质量", "音频质量"])
        self.table.horizontalHeader().setStretchLastSection(True)
        table_layout.addWidget(self.table)

        main_layout.addWidget(table_group)

        # 下载选项
        options_group = QGroupBox("下载选项")
        options_layout = QVBoxLayout(options_group)

        cookie_layout = QHBoxLayout()
        self.use_cookie_checkbox = QRadioButton("使用Cookie")
        cookie_layout.addWidget(self.use_cookie_checkbox)
        cookie_layout.addStretch()
        options_layout.addLayout(cookie_layout)

        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("下载目录:"))
        self.dir_input = QLineEdit()
        self.dir_input.setReadOnly(True)
        self.dir_input.setPlaceholderText("请选择下载目录")
        dir_layout.addWidget(self.dir_input)
        self.browse_button = QPushButton("浏览")
        self.browse_button.clicked.connect(self.browse_download_dir)
        dir_layout.addWidget(self.browse_button)
        options_layout.addLayout(dir_layout)

        main_layout.addWidget(options_group)

        # 进度区域
        progress_group = QGroupBox("下载进度")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        self.status_label = QLabel("准备就绪")
        progress_layout.addWidget(self.status_label)
        main_layout.addWidget(progress_group)

        # 按钮区域
        button_layout = QHBoxLayout()
        self.download_button = QPushButton("开始下载")
        self.download_button.clicked.connect(self.start_download)
        self.download_button.setEnabled(False)
        button_layout.addWidget(self.download_button)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

        main_layout.addStretch()

        self.dir_input.textChanged.connect(self.check_download_button)

    def update_status(self, message: str):
        self.status_label.setText(message)
        if self.status_bar:
            self.status_bar.showMessage(message)

    def parse_video_infos(self):
        """解析多条视频信息"""
        text = self.url_input.toPlainText().strip()
        urls = [u.strip() for u in text.splitlines() if u.strip()]
        if not urls:
            QMessageBox.warning(self, "错误", "请输入至少一个视频链接")
            return

        self.table.setRowCount(0)
        self.parse_button.setEnabled(False)

        # 创建并启动解析线程
        self.parse_thread = self.BatchParseThread(self.video_info_parser, urls)
        self.parse_thread.video_parsed.connect(self.on_video_parsed)
        self.parse_thread.progress_updated.connect(self.update_status)
        self.parse_thread.parse_finished.connect(self.on_parse_finished)
        self.parse_thread.start()

    def on_video_parsed(self, index: int, basic: dict, formats: list):
        """单个视频解析完成回调"""
        row = self.table.rowCount()
        self.table.insertRow(row)

        if 'error' in basic:
            self.table.setItem(row, 0, QTableWidgetItem(str(index)))
            self.table.setItem(row, 1, QTableWidgetItem("解析失败"))
            self.table.setItem(row, 2, QTableWidgetItem("-"))
            self.table.setItem(row, 3, QTableWidgetItem(basic['error']))
            return

        self.table.setItem(row, 0, QTableWidgetItem(str(index)))
        self.table.setItem(row, 1, QTableWidgetItem(basic['title']))
        self.table.setItem(row, 2, QTableWidgetItem(
            self.video_info_parser.format_duration(basic['duration'])
        ))

        video_combo = QComboBox()
        video_combo.addItem("最高画质 (自动)", "best")
        audio_combo = QComboBox()
        audio_combo.addItem("最高音质 (自动)", "best")
        for fmt in formats:
            if isinstance(fmt, dict):
                if fmt.get('type') == 'video':
                    video_combo.addItem(fmt['display'], fmt['format_id'])
                elif fmt.get('type') == 'audio':
                    audio_combo.addItem(fmt['display'], fmt['format_id'])
        self.table.setCellWidget(row, 3, video_combo)
        self.table.setCellWidget(row, 4, audio_combo)

    def on_parse_finished(self):
        self.parse_button.setEnabled(True)

    class BatchDownloadThread(QThread):
        """批量下载线程"""
        progress_updated = pyqtSignal(float, str, str, int, int)
        status_updated = pyqtSignal(str)
        download_completed = pyqtSignal()
        download_error = pyqtSignal(str)

        def __init__(self, downloader: VideoDownloader, tasks: list, output_dir: str,
                     use_cookies: bool = False, cookies_file: str = None,
                     prefer_mp4: bool = True):
            super().__init__()
            self.downloader = downloader
            self.tasks = tasks
            self.output_dir = output_dir
            self.use_cookies = use_cookies
            self.cookies_file = cookies_file
            self.prefer_mp4 = prefer_mp4
            self.is_cancelled = False
            self.current_index = 0
            self.total = len(tasks)
            self._success = True
            self._error = ""

        def run(self):
            try:
                for idx, (url, vfmt, afmt) in enumerate(self.tasks, start=1):
                    if self.is_cancelled:
                        break
                    self.current_index = idx
                    self.downloader.set_callbacks(
                        progress_callback=self._progress_callback,
                        completion_callback=self._completion_callback,
                        error_callback=self._error_callback
                    )
                    fmt = f"{vfmt}+{afmt}" if afmt else vfmt
                    self.downloader.download_videos(
                        urls=[url],
                        output_dir=self.output_dir,
                        format_id=fmt,
                        use_cookies=self.use_cookies,
                        cookies_file=self.cookies_file,
                        prefer_mp4=self.prefer_mp4
                    )
                    if self.downloader.download_thread:
                        self.downloader.download_thread.join()
                    if not self._success:
                        self.download_error.emit(self._error or "下载失败")
                        return
                if not self.is_cancelled:
                    self.download_completed.emit()
            except Exception as e:
                self.download_error.emit(str(e))

        def _progress_callback(self, progress: float, speed: str, eta: str,
                               video_title: str, video_index: int, total_videos: int):
            self.progress_updated.emit(progress, speed, eta, self.current_index, self.total)
            status = f"下载中... {self.current_index}/{self.total}"
            self.status_updated.emit(status)

        def _completion_callback(self, success: bool, result: str):
            self._success = success
            if not success:
                self._error = result

        def _error_callback(self, error_message: str):
            self._success = False
            self._error = error_message

        def cancel(self):
            self.is_cancelled = True
            self.downloader.cancel_download()

    def check_download_button(self):
        self.download_button.setEnabled(bool(self.dir_input.text()) and not self.is_downloading)

    def start_download(self):
        text = self.url_input.toPlainText().strip()
        urls = [u.strip() for u in text.splitlines() if u.strip()]
        if not urls:
            QMessageBox.warning(self, "错误", "请输入至少一个视频链接")
            return

        output_dir = self.dir_input.text()
        if not output_dir:
            QMessageBox.warning(self, "错误", "请选择下载目录")
            return

        tasks = []
        for row, url in enumerate(urls):
            if row >= self.table.rowCount():
                continue
            video_combo = self.table.cellWidget(row, 3)
            audio_combo = self.table.cellWidget(row, 4)
            vfmt = video_combo.currentData() if isinstance(video_combo, QComboBox) else "best"
            afmt = audio_combo.currentData() if isinstance(audio_combo, QComboBox) else "best"
            tasks.append((url, vfmt, afmt))

        self.download_thread = self.BatchDownloadThread(
            downloader=self.downloader,
            tasks=tasks,
            output_dir=output_dir,
            use_cookies=self.use_cookie_checkbox.isChecked(),
            cookies_file=self.cookie_manager.get_cookie_file() if self.use_cookie_checkbox.isChecked() else None
        )
        self.download_thread.progress_updated.connect(self.update_progress)
        self.download_thread.status_updated.connect(self.update_status)
        self.download_thread.download_completed.connect(self.on_download_completed)
        self.download_thread.download_error.connect(self.on_download_error)

        self.is_downloading = True
        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在准备下载...")
        self.download_thread.start()

    def update_progress(self, progress: float, speed: str, eta: str, index: int, total: int):
        self.progress_bar.setValue(int(progress))
        self.status_label.setText(
            f"下载中... {index}/{total} {progress:.1f}% - {speed} - 剩余时间: {eta}"
        )

    def on_download_completed(self):
        self.is_downloading = False
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status_label.setText("下载完成")

    def on_download_error(self, error_message: str):
        self.is_downloading = False
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status_label.setText("下载失败")
        QMessageBox.critical(self, "错误", f"下载失败：{error_message}")

    def cancel_download(self):
        if self.download_thread:
            self.download_thread.cancel()
            self.download_thread.wait()
        self.is_downloading = False
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status_label.setText("下载已取消")

    def set_default_download_dir(self):
        last_dir = self.config_manager.get('download_dir')
        if not last_dir:
            last_dir = os.path.join(os.path.expanduser('~'), 'Desktop')
        if not os.path.exists(last_dir):
            last_dir = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.dir_input.setText(last_dir)
        self.config_manager.set('download_dir', last_dir)

    def browse_download_dir(self):
        current_dir = self.dir_input.text() or os.path.join(os.path.expanduser('~'), 'Desktop')
        dir_path = QFileDialog.getExistingDirectory(self, "选择下载文件夹", current_dir)
        if dir_path:
            self.dir_input.setText(dir_path)
            self.config_manager.set('download_dir', dir_path)

