"""
YouTube Downloader URL 输入组件
提供 URL 输入和验证功能
"""
import re
from typing import Tuple, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QCheckBox, QGroupBox, QLabel
)
from PyQt5.QtCore import pyqtSignal, Qt

from src.core.event_bus import event_bus, Events


class UrlInputWidget(QWidget):
    """URL 输入组件"""
    
    # 信号定义
    url_validated = pyqtSignal(str)           # URL 验证通过
    parse_requested = pyqtSignal(str, bool)   # 请求解析 (url, use_cookie)
    validation_failed = pyqtSignal(str)       # 验证失败 (错误信息)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建分组框
        group_box = QGroupBox("视频链接")
        group_layout = QVBoxLayout(group_box)
        
        # URL 输入框
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("在此输入 YouTube 视频链接")
        self.url_input.setMinimumHeight(80)
        self.url_input.setMaximumHeight(120)
        group_layout.addWidget(self.url_input)
        
        # Cookie 复选框
        self.use_cookie_checkbox = QCheckBox("使用 Cookie (用于会员或年龄限制视频)")
        self.use_cookie_checkbox.setChecked(False)
        group_layout.addWidget(self.use_cookie_checkbox)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.clear_button = QPushButton("清空")
        self.clear_button.setFixedWidth(80)
        self.clear_button.clicked.connect(self.clear_input)
        button_layout.addWidget(self.clear_button)
        
        self.parse_button = QPushButton("解析视频信息")
        self.parse_button.clicked.connect(self._on_parse_clicked)
        button_layout.addWidget(self.parse_button)
        
        group_layout.addLayout(button_layout)
        
        layout.addWidget(group_box)
    
    def _on_parse_clicked(self):
        """解析按钮点击事件"""
        url = self.get_url()
        if not url:
            self.validation_failed.emit("请输入视频链接")
            return
        
        # 验证 URL
        is_valid, error_msg = self.validate_url(url)
        if not is_valid:
            self.validation_failed.emit(error_msg)
            return
        
        # 发送解析请求信号
        use_cookie = self.use_cookie_checkbox.isChecked()
        self.url_validated.emit(url)
        self.parse_requested.emit(url, use_cookie)
        
        # 发布事件
        event_bus.emit(Events.VIDEO_PARSE_STARTED, url=url, use_cookie=use_cookie)
    
    def get_url(self) -> str:
        """获取输入的 URL（清理后）"""
        text = self.url_input.toPlainText().strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines[0] if lines else ""
    
    def get_urls(self) -> list:
        """获取所有输入的 URL"""
        text = self.url_input.toPlainText().strip()
        return [line.strip() for line in text.splitlines() if line.strip()]
    
    def set_url(self, url: str):
        """设置 URL"""
        self.url_input.setPlainText(url)
    
    def clear_input(self):
        """清空输入"""
        self.url_input.clear()
    
    def is_using_cookie(self) -> bool:
        """是否使用 Cookie"""
        return self.use_cookie_checkbox.isChecked()
    
    def set_use_cookie(self, use: bool):
        """设置是否使用 Cookie"""
        self.use_cookie_checkbox.setChecked(use)
    
    def set_enabled(self, enabled: bool):
        """设置组件启用状态"""
        self.url_input.setEnabled(enabled)
        self.parse_button.setEnabled(enabled)
        self.use_cookie_checkbox.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
    
    def set_parsing(self, is_parsing: bool):
        """设置解析状态"""
        self.parse_button.setEnabled(not is_parsing)
        if is_parsing:
            self.parse_button.setText("解析中...")
        else:
            self.parse_button.setText("解析视频信息")
    
    @staticmethod
    def validate_url(url: str) -> Tuple[bool, str]:
        """
        验证 URL 是否为有效的 YouTube 视频链接
        
        Args:
            url: 要验证的 URL
            
        Returns:
            (是否有效, 错误信息)
        """
        # 检查是否以 http(s) 开头
        if not re.match(r'https?://', url):
            return False, "请输入有效的链接，应以 http:// 或 https:// 开头"
        
        # 检查是否是 YouTube 链接
        youtube_regex = re.compile(
            r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
        )
        if not youtube_regex.match(url):
            return False, "请输入有效的 YouTube 视频链接"
        
        # 检查是否包含视频 ID
        if 'watch?v=' not in url and 'youtu.be/' not in url and '/shorts/' not in url:
            return False, "链接格式不正确，似乎不是一个有效的 YouTube 视频链接"
        
        return True, ""
    
    def is_playlist_url(self, url: str = None) -> bool:
        """检查是否为播放列表 URL"""
        url = url or self.get_url()
        return 'playlist' in url or '&list=' in url
    
    def has_multiple_urls(self) -> bool:
        """是否有多个 URL"""
        return len(self.get_urls()) > 1

