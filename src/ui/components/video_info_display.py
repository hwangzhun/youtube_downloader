"""
YouTube Downloader 视频信息显示组件
提供视频信息展示功能
"""
from typing import Optional, Dict

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QGroupBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

from src.core.event_bus import event_bus, Events


class VideoInfoDisplayWidget(QWidget):
    """视频信息显示组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._video_info: Optional[Dict] = None
        self._init_ui()
        self._connect_events()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建分组框
        group_box = QGroupBox("视频信息")
        group_layout = QVBoxLayout(group_box)
        
        # 标题
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("标题:"))
        self.title_label = QLabel("未解析")
        self.title_label.setWordWrap(True)
        self.title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        title_layout.addWidget(self.title_label, 1)
        group_layout.addLayout(title_layout)
        
        # 时长
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("时长:"))
        self.duration_label = QLabel("未解析")
        duration_layout.addWidget(self.duration_label)
        duration_layout.addStretch()
        group_layout.addLayout(duration_layout)
        
        # 上传者
        uploader_layout = QHBoxLayout()
        uploader_layout.addWidget(QLabel("上传者:"))
        self.uploader_label = QLabel("")
        uploader_layout.addWidget(self.uploader_label)
        uploader_layout.addStretch()
        group_layout.addLayout(uploader_layout)
        
        # 额外信息（可选显示）
        self.extra_info_frame = QFrame()
        self.extra_info_frame.setVisible(False)
        extra_layout = QVBoxLayout(self.extra_info_frame)
        extra_layout.setContentsMargins(0, 5, 0, 0)
        
        # 观看次数
        views_layout = QHBoxLayout()
        views_layout.addWidget(QLabel("观看次数:"))
        self.views_label = QLabel("")
        views_layout.addWidget(self.views_label)
        views_layout.addStretch()
        extra_layout.addLayout(views_layout)
        
        # 点赞数
        likes_layout = QHBoxLayout()
        likes_layout.addWidget(QLabel("点赞数:"))
        self.likes_label = QLabel("")
        likes_layout.addWidget(self.likes_label)
        likes_layout.addStretch()
        extra_layout.addLayout(likes_layout)
        
        group_layout.addWidget(self.extra_info_frame)
        
        layout.addWidget(group_box)
    
    def _connect_events(self):
        """连接事件总线事件"""
        event_bus.subscribe(Events.VIDEO_PARSE_COMPLETED, self._on_video_parsed)
    
    def _on_video_parsed(self, event):
        """处理视频解析完成事件"""
        video_info = event.data.get('video_info')
        if video_info:
            self.set_video_info(video_info)
    
    def set_video_info(self, video_info: Dict):
        """
        设置视频信息
        
        Args:
            video_info: 视频信息字典
        """
        self._video_info = video_info
        
        # 设置标题
        title = video_info.get('title', '未知标题')
        self.title_label.setText(title)
        
        # 设置时长
        duration = video_info.get('duration', 0)
        self.duration_label.setText(self._format_duration(duration))
        
        # 设置上传者
        uploader = video_info.get('uploader', '')
        if uploader:
            self.uploader_label.setText(uploader)
            self.uploader_label.parent().setVisible(True)
        else:
            self.uploader_label.parent().setVisible(False)
        
        # 设置额外信息
        view_count = video_info.get('view_count')
        like_count = video_info.get('like_count')
        
        if view_count is not None or like_count is not None:
            self.extra_info_frame.setVisible(True)
            
            if view_count is not None:
                self.views_label.setText(self._format_count(view_count))
            
            if like_count is not None:
                self.likes_label.setText(self._format_count(like_count))
        else:
            self.extra_info_frame.setVisible(False)
    
    def clear(self):
        """清空信息"""
        self._video_info = None
        self.title_label.setText("未解析")
        self.duration_label.setText("未解析")
        self.uploader_label.setText("")
        self.views_label.setText("")
        self.likes_label.setText("")
        self.extra_info_frame.setVisible(False)
    
    def set_loading(self):
        """设置为加载中状态"""
        self.title_label.setText("正在解析...")
        self.duration_label.setText("--:--")
    
    def set_error(self, error_msg: str = "解析失败"):
        """设置为错误状态"""
        self.title_label.setText(error_msg)
        self.duration_label.setText("--:--")
    
    def set_live(self, title: str):
        """设置为直播状态"""
        self.title_label.setText(f"{title} (直播中)")
        self.duration_label.setText("直播")
    
    def get_video_info(self) -> Optional[Dict]:
        """获取视频信息"""
        return self._video_info
    
    def has_info(self) -> bool:
        """是否有视频信息"""
        return self._video_info is not None
    
    @staticmethod
    def _format_duration(seconds: int) -> str:
        """格式化时长"""
        if not seconds or seconds <= 0:
            return "未知时长"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def _format_count(count: int) -> str:
        """格式化数量"""
        if count is None:
            return "未知"
        
        if count >= 1_000_000_000:
            return f"{count / 1_000_000_000:.1f}B"
        elif count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        elif count >= 1_000:
            return f"{count / 1_000:.1f}K"
        return str(count)

