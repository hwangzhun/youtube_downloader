"""
YouTube Downloader 格式选择组件
提供视频和音频格式选择功能
"""
from typing import Optional, List, Dict, Tuple

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
    QLabel, QGroupBox, QLineEdit, QPushButton, QFileDialog
)
from PyQt5.QtCore import pyqtSignal
import os


class FormatSelectorWidget(QWidget):
    """格式选择组件"""
    
    # 信号定义
    format_changed = pyqtSignal(str, str)      # 格式改变 (video_id, audio_id)
    output_dir_changed = pyqtSignal(str)       # 输出目录改变
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._video_formats: List[Dict] = []
        self._audio_formats: List[Dict] = []
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建分组框
        group_box = QGroupBox("下载选项")
        group_layout = QVBoxLayout(group_box)
        
        # 视频质量选择
        video_layout = QHBoxLayout()
        video_layout.addWidget(QLabel("视频质量:"))
        self.video_combo = QComboBox()
        self.video_combo.setEnabled(False)
        self.video_combo.currentIndexChanged.connect(self._on_format_changed)
        video_layout.addWidget(self.video_combo, 1)
        group_layout.addLayout(video_layout)
        
        # 音频质量选择
        audio_layout = QHBoxLayout()
        audio_layout.addWidget(QLabel("音频质量:"))
        self.audio_combo = QComboBox()
        self.audio_combo.setEnabled(False)
        self.audio_combo.currentIndexChanged.connect(self._on_format_changed)
        audio_layout.addWidget(self.audio_combo, 1)
        group_layout.addLayout(audio_layout)
        
        # 下载目录选择
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("下载目录:"))
        self.dir_input = QLineEdit()
        self.dir_input.setReadOnly(True)
        self.dir_input.setPlaceholderText("请选择下载目录")
        self.dir_input.textChanged.connect(lambda t: self.output_dir_changed.emit(t))
        dir_layout.addWidget(self.dir_input, 1)
        
        self.browse_button = QPushButton("浏览")
        self.browse_button.clicked.connect(self._browse_directory)
        dir_layout.addWidget(self.browse_button)
        group_layout.addLayout(dir_layout)
        
        layout.addWidget(group_box)
    
    def _on_format_changed(self):
        """格式选择改变事件"""
        video_id = self.get_video_format_id()
        audio_id = self.get_audio_format_id()
        self.format_changed.emit(video_id, audio_id)
    
    def _browse_directory(self):
        """浏览目录"""
        current_dir = self.dir_input.text() or os.path.expanduser("~/Desktop")
        
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择下载文件夹",
            current_dir
        )
        
        if dir_path:
            self.dir_input.setText(dir_path)
    
    def set_video_formats(self, formats: List[Dict]):
        """
        设置视频格式选项
        
        Args:
            formats: 格式列表，每个格式应包含 'format_id' 和 'display' 键
        """
        self._video_formats = formats
        self.video_combo.clear()
        self.video_combo.setEnabled(True)
        
        # 添加自动选择选项
        self.video_combo.addItem("最高画质 (自动选择)", "best")
        
        # 添加格式选项
        for fmt in formats:
            if fmt.get('type') == 'video':
                display = fmt.get('display', fmt.get('format_id', '未知'))
                self.video_combo.addItem(display, fmt.get('format_id'))
    
    def set_audio_formats(self, formats: List[Dict]):
        """
        设置音频格式选项
        
        Args:
            formats: 格式列表，每个格式应包含 'format_id' 和 'display' 键
        """
        self._audio_formats = formats
        self.audio_combo.clear()
        self.audio_combo.setEnabled(True)
        
        # 添加自动选择选项
        self.audio_combo.addItem("最高音质 (自动选择)", "best")
        
        # 添加格式选项
        for fmt in formats:
            if fmt.get('type') == 'audio':
                display = fmt.get('display', fmt.get('format_id', '未知'))
                self.audio_combo.addItem(display, fmt.get('format_id'))
    
    def set_formats(self, formats: List[Dict]):
        """
        设置所有格式选项（自动分类为视频和音频）
        
        Args:
            formats: 格式列表
        """
        video_formats = [f for f in formats if f.get('type') == 'video']
        audio_formats = [f for f in formats if f.get('type') == 'audio']
        
        self.set_video_formats(video_formats)
        self.set_audio_formats(audio_formats)
    
    def get_video_format_id(self) -> str:
        """获取选中的视频格式 ID"""
        return self.video_combo.currentData() or "best"
    
    def get_audio_format_id(self) -> str:
        """获取选中的音频格式 ID"""
        return self.audio_combo.currentData() or "best"
    
    def get_format_ids(self) -> Tuple[str, str]:
        """获取视频和音频格式 ID"""
        return self.get_video_format_id(), self.get_audio_format_id()
    
    def get_output_dir(self) -> str:
        """获取输出目录"""
        return self.dir_input.text()
    
    def set_output_dir(self, path: str):
        """设置输出目录"""
        self.dir_input.setText(path)
    
    def clear_formats(self):
        """清空格式选项"""
        self.video_combo.clear()
        self.video_combo.setEnabled(False)
        self.audio_combo.clear()
        self.audio_combo.setEnabled(False)
        self._video_formats = []
        self._audio_formats = []
    
    def set_enabled(self, enabled: bool):
        """设置组件启用状态"""
        self.video_combo.setEnabled(enabled and len(self._video_formats) > 0)
        self.audio_combo.setEnabled(enabled and len(self._audio_formats) > 0)
        self.dir_input.setEnabled(enabled)
        self.browse_button.setEnabled(enabled)
    
    def is_ready(self) -> bool:
        """检查是否准备好下载（目录已设置）"""
        return bool(self.dir_input.text())

