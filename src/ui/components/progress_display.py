"""
YouTube Downloader 进度显示组件
提供下载进度和状态显示功能
"""
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, 
    QLabel, QGroupBox, QPushButton
)
from PyQt5.QtCore import pyqtSignal, Qt

from src.core.event_bus import event_bus, Events
from src.types import DownloadStatus


class ProgressDisplayWidget(QWidget):
    """进度显示组件"""
    
    # 信号定义
    download_requested = pyqtSignal()      # 请求下载
    cancel_requested = pyqtSignal()        # 请求取消
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = DownloadStatus.PENDING
        self._init_ui()
        self._connect_events()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建分组框
        group_box = QGroupBox("下载进度")
        group_layout = QVBoxLayout(group_box)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        group_layout.addWidget(self.progress_bar)
        
        # 状态信息
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("准备就绪")
        status_layout.addWidget(self.status_label, 1)
        
        self.speed_label = QLabel("")
        self.speed_label.setAlignment(Qt.AlignRight)
        status_layout.addWidget(self.speed_label)
        
        self.eta_label = QLabel("")
        self.eta_label.setAlignment(Qt.AlignRight)
        self.eta_label.setMinimumWidth(80)
        status_layout.addWidget(self.eta_label)
        
        group_layout.addLayout(status_layout)
        
        layout.addWidget(group_box)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.download_button = QPushButton("开始下载")
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self._on_download_clicked)
        button_layout.addWidget(self.download_button)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def _connect_events(self):
        """连接事件总线事件"""
        event_bus.subscribe(Events.DOWNLOAD_PROGRESS, self._on_download_progress)
        event_bus.subscribe(Events.DOWNLOAD_COMPLETED, self._on_download_completed)
        event_bus.subscribe(Events.DOWNLOAD_FAILED, self._on_download_failed)
    
    def _on_download_clicked(self):
        """下载按钮点击"""
        self.download_requested.emit()
    
    def _on_cancel_clicked(self):
        """取消按钮点击"""
        self.cancel_requested.emit()
    
    def _on_download_progress(self, event):
        """处理下载进度事件"""
        data = event.data
        self.update_progress(
            progress=data.get('progress', 0),
            speed=data.get('speed', ''),
            eta=data.get('eta', '')
        )
    
    def _on_download_completed(self, event):
        """处理下载完成事件"""
        self.set_completed()
    
    def _on_download_failed(self, event):
        """处理下载失败事件"""
        error_msg = event.data.get('error', '下载失败')
        self.set_failed(error_msg)
    
    def update_progress(self, progress: float, speed: str = "", eta: str = ""):
        """
        更新进度
        
        Args:
            progress: 进度百分比 (0-100)
            speed: 下载速度
            eta: 预计剩余时间
        """
        self.progress_bar.setValue(int(progress))
        self.status_label.setText(f"下载中... {progress:.1f}%")
        
        if speed:
            self.speed_label.setText(speed)
        if eta:
            self.eta_label.setText(f"剩余: {eta}")
    
    def set_status(self, status: str):
        """设置状态文本"""
        self.status_label.setText(status)
    
    def set_downloading(self):
        """设置为下载中状态"""
        self._status = DownloadStatus.DOWNLOADING
        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_label.setText("正在准备下载...")
        self.progress_bar.setValue(0)
        self.speed_label.setText("")
        self.eta_label.setText("")
    
    def set_completed(self):
        """设置为完成状态"""
        self._status = DownloadStatus.COMPLETED
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(100)
        self.status_label.setText("下载完成")
        self.speed_label.setText("")
        self.eta_label.setText("")
    
    def set_failed(self, error_msg: str = "下载失败"):
        """设置为失败状态"""
        self._status = DownloadStatus.FAILED
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText(error_msg)
        self.speed_label.setText("")
        self.eta_label.setText("")
    
    def set_cancelled(self):
        """设置为已取消状态"""
        self._status = DownloadStatus.CANCELLED
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("下载已取消")
        self.speed_label.setText("")
        self.eta_label.setText("")
    
    def reset(self):
        """重置状态"""
        self._status = DownloadStatus.PENDING
        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("准备就绪")
        self.speed_label.setText("")
        self.eta_label.setText("")
    
    def set_ready(self, ready: bool = True):
        """设置是否准备好下载"""
        if self._status not in (DownloadStatus.DOWNLOADING,):
            self.download_button.setEnabled(ready)
    
    def is_downloading(self) -> bool:
        """是否正在下载"""
        return self._status == DownloadStatus.DOWNLOADING
    
    def get_status(self) -> DownloadStatus:
        """获取当前状态"""
        return self._status

