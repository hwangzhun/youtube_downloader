"""
批量下载标签页模块
提供解析多条视频信息并选择质量的界面
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTextEdit, QPushButton,
    QMessageBox, QTableWidget, QTableWidgetItem, QComboBox, QLabel, QStatusBar
)
from PyQt5.QtCore import Qt

from src.core.video_info.video_info_parser import VideoInfoParser
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

        self.init_ui()

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

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["序号", "标题", "时长", "视频质量"])
        self.table.horizontalHeader().setStretchLastSection(True)
        table_layout.addWidget(self.table)

        main_layout.addWidget(table_group)

        # 提示信息
        self.status_label = QLabel("准备就绪")
        main_layout.addWidget(self.status_label)

        main_layout.addStretch()

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
        for index, url in enumerate(urls, start=1):
            try:
                self.update_status(f"正在解析第 {index} 个视频...")
                video_info = self.video_info_parser.parse_video(url)
                basic = self.video_info_parser.get_basic_info(video_info)
                formats = self.video_info_parser.get_available_formats(video_info)
                formatted = self.video_info_parser.get_formatted_formats(formats)
            except Exception as e:
                self.logger.error(f"解析失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"解析失败：{str(e)}")
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(index)))
            self.table.setItem(row, 1, QTableWidgetItem(basic['title']))
            self.table.setItem(row, 2, QTableWidgetItem(
                self.video_info_parser.format_duration(basic['duration'])
            ))

            combo = QComboBox()
            combo.addItem("最高画质 (自动)", "best")
            for fmt in formatted:
                if fmt['type'] == 'video':
                    combo.addItem(fmt['display'], fmt['format_id'])
            self.table.setCellWidget(row, 3, combo)

        self.update_status("解析完成")
