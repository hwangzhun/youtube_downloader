from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QProgressBar, QFileDialog, QRadioButton, QComboBox, QMessageBox, QGroupBox,
    QLineEdit
)
from PyQt5.QtCore import Qt
import os

from src.core.downloader import VideoDownloader
from src.core.video_info.video_info_parser import VideoInfoParser
from src.utils.config import ConfigManager
from src.utils.logger import LoggerManager

class MultiDownloadTab(QWidget):
    """多视频下载标签页"""

    def __init__(self, config_manager: ConfigManager, status_bar=None, cookie_tab=None):
        super().__init__()
        self.config_manager = config_manager
        self.status_bar = status_bar
        self.cookie_tab = cookie_tab

        self.logger = LoggerManager().get_logger()

        self.downloader = VideoDownloader()
        self.video_info_parser = VideoInfoParser()

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        input_group = QGroupBox("视频链接 (每行一个)")
        input_layout = QVBoxLayout(input_group)
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("在此输入多个链接...\n每行一个")
        input_layout.addWidget(self.url_input)
        parse_button = QPushButton("解析视频信息")
        parse_button.clicked.connect(self.parse_video_info)
        input_layout.addWidget(parse_button)
        layout.addWidget(input_group)

        options_group = QGroupBox("下载选项")
        options_layout = QVBoxLayout(options_group)
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("视频质量:"))
        self.video_quality_combo = QComboBox()
        quality_layout.addWidget(self.video_quality_combo)
        options_layout.addLayout(quality_layout)

        cookie_layout = QHBoxLayout()
        self.use_cookie_checkbox = QRadioButton("使用Cookie")
        cookie_layout.addWidget(self.use_cookie_checkbox)
        fetch_btn = QPushButton("获取Cookie")
        fetch_btn.clicked.connect(self.fetch_cookies)
        cookie_layout.addWidget(fetch_btn)
        cookie_layout.addStretch()
        options_layout.addLayout(cookie_layout)

        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("下载目录:"))
        self.dir_input = QLineEdit()
        self.dir_input.setReadOnly(True)
        dir_layout.addWidget(self.dir_input)
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_download_dir)
        dir_layout.addWidget(browse_btn)
        options_layout.addLayout(dir_layout)

        layout.addWidget(options_group)

        progress_group = QGroupBox("下载进度")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        self.status_label = QLabel("就绪")
        progress_layout.addWidget(self.status_label)
        layout.addWidget(progress_group)

        btn_layout = QHBoxLayout()
        self.download_button = QPushButton("开始下载")
        self.download_button.clicked.connect(self.start_download)
        btn_layout.addWidget(self.download_button)
        layout.addLayout(btn_layout)

        self.set_default_download_dir()

    def update_status_message(self, message: str):
        if self.status_bar:
            self.status_bar.showMessage(message)

    def parse_video_info(self):
        urls = [u.strip() for u in self.url_input.toPlainText().splitlines() if u.strip()]
        if not urls:
            QMessageBox.warning(self, "错误", "请输入至少一个视频链接")
            return
        # 解析第一条链接用于获取可用格式
        try:
            info = self.video_info_parser.parse_video(urls[0])
            formats = self.video_info_parser.get_available_formats(info)
            formatted = self.video_info_parser.get_formatted_formats(formats)
            self.video_quality_combo.clear()
            self.video_quality_combo.addItem("最高画质 (自动)", "best")
            for f in formatted:
                if f['type'] == 'video':
                    self.video_quality_combo.addItem(f['display'], f['format_id'])
            self.status_label.setText(f"解析完成，共 {len(urls)} 条链接")
            self.update_status_message("解析完成")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"解析失败: {str(e)}")
            self.status_label.setText("解析失败")

    def start_download(self):
        urls = [u.strip() for u in self.url_input.toPlainText().splitlines() if u.strip()]
        if not urls:
            QMessageBox.warning(self, "错误", "请输入视频链接")
            return
        output_dir = self.dir_input.text()
        if not output_dir:
            QMessageBox.warning(self, "错误", "请选择下载目录")
            return
        format_id = self.video_quality_combo.currentData() or 'best'
        self.status_label.setText("开始下载...")
        self.update_status_message("开始下载")
        use_ck = self.use_cookie_checkbox.isChecked()
        cookie_file = self.cookie_tab.get_cookie_file() if use_ck and self.cookie_tab else None
        self.downloader.download_videos(urls, output_dir, format_id=format_id,
                                        use_cookies=use_ck, cookies_file=cookie_file)
        self.status_label.setText("下载完成")
        self.update_status_message("下载完成")

    def browse_download_dir(self):
        current_dir = self.dir_input.text() or os.path.join(os.path.expanduser('~'), 'Desktop')
        dir_path = QFileDialog.getExistingDirectory(self, "选择下载文件夹", current_dir)
        if dir_path:
            self.dir_input.setText(dir_path)
            self.config_manager.set('download_dir', dir_path)

    def set_default_download_dir(self):
        last_dir = self.config_manager.get('download_dir') or os.path.join(os.path.expanduser('~'), 'Desktop')
        if not os.path.exists(last_dir):
            last_dir = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.dir_input.setText(last_dir)
        self.config_manager.set('download_dir', last_dir)

    def fetch_cookies(self):
        if self.cookie_tab:
            self.cookie_tab.get_youtube_cookies()
