"""
YouTube Downloader 频道下载标签页模块
支持输入频道URL并下载该频道的所有视频
"""
import os
import re
import threading
from typing import Optional, List, Dict, Tuple
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QProgressBar, QFileDialog, QComboBox, QMessageBox, QGroupBox,
    QApplication, QStatusBar, QCheckBox, QTextEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QStyle

from src.core.downloader import VideoDownloader
from src.core.download_queue import QueuedTask
from src.core.video_info.video_info_parser import VideoInfoParser
from src.utils.config import ConfigManager
from src.utils.logger import LoggerManager
from src.utils.error_messages import ErrorMessages
from src.types import DownloadStatus, DownloadPriority


class ChannelVideosThread(QThread):
    """频道视频获取线程"""
    
    # 信号定义
    channel_info_retrieved = pyqtSignal(dict)      # 频道信息
    videos_retrieved = pyqtSignal(list)           # 视频列表
    progress_updated = pyqtSignal(int, int, str)    # 当前, 总数, 状态
    error_occurred = pyqtSignal(str)               # 错误信息
    paused_changed = pyqtSignal(bool)              # 暂停状态变化
    
    def __init__(self, channel_url: str, video_info_parser: VideoInfoParser,
                 use_cookies: bool = False, cookies_file: str = None, proxy_url: str = None):
        super().__init__()
        self.channel_url = channel_url
        self.video_info_parser = video_info_parser
        self.use_cookies = use_cookies
        self.cookies_file = cookies_file
        self.proxy_url = proxy_url
        self.is_cancelled = False
        self.is_paused = False
        self._pause_lock = threading.Event()
        self._pause_lock.set()  # 初始为非暂停状态
        self.logger = LoggerManager().get_logger()
    
    def run(self):
        """执行频道视频获取"""
        try:
            # 等待暂停解除
            self._wait_if_paused()
            if self.is_cancelled:
                return
            
            # 获取频道信息（先获取一个视频来获取频道信息）
            self.progress_updated.emit(0, 0, "正在获取频道信息...")
            try:
                # 获取频道视频列表
                self.progress_updated.emit(0, 0, "正在获取频道视频列表...")
                videos = self.video_info_parser.get_channel_videos(
                    self.channel_url,
                    self.use_cookies,
                    self.cookies_file,
                    self.proxy_url
                )
                
                if self.is_cancelled:
                    return
                
                # 提取频道信息（从第一个视频获取）
                channel_info = {
                    'url': self.channel_url,
                    'video_count': len(videos),
                    'uploader': videos[0].get('uploader', '未知频道') if videos else '未知频道'
                }
                
                # 发送频道信息
                self.channel_info_retrieved.emit(channel_info)
                
                # 发送视频列表
                if videos:
                    self.videos_retrieved.emit(videos)
                
            except Exception as e:
                self.logger.error(f"获取频道视频失败: {str(e)}")
                self.error_occurred.emit(str(e))
                
        except Exception as e:
            self.logger.error(f"频道视频获取线程出错: {str(e)}")
            self.error_occurred.emit(str(e))
    
    def _wait_if_paused(self):
        """如果暂停则等待"""
        while self.is_paused and not self.is_cancelled:
            self._pause_lock.wait(0.5)  # 每0.5秒检查一次
    
    def cancel(self):
        """取消获取"""
        self.is_cancelled = True
        self.is_paused = False
        self._pause_lock.set()
    
    def pause(self):
        """暂停获取"""
        if not self.is_paused:
            self.is_paused = True
            self._pause_lock.clear()
            self.paused_changed.emit(True)
            self.logger.info("获取已暂停")
    
    def resume(self):
        """恢复获取"""
        if self.is_paused:
            self.is_paused = False
            self._pause_lock.set()
            self.paused_changed.emit(False)
            self.logger.info("获取已恢复")


class ChannelDownloadTab(QWidget):
    """频道下载标签页"""
    
    def __init__(self, config_manager: ConfigManager = None,
                 status_bar: QStatusBar = None, cookie_tab=None):
        super().__init__()
        
        # 初始化日志和配置
        self.logger = LoggerManager().get_logger()
        self.config_manager = config_manager or ConfigManager()
        self.status_bar = status_bar
        self.cookie_tab = cookie_tab
        
        # 初始化核心组件
        self.video_info_parser = VideoInfoParser()
        
        # 频道信息
        self.channel_info: Optional[Dict] = None
        self.channel_videos: List[Dict] = []
        
        # 线程
        self.channel_thread: Optional[ChannelVideosThread] = None
        
        # 初始化 UI
        self._init_ui()
        
        # 设置默认下载目录
        self._set_default_download_dir()
        
        self.logger.info("频道下载标签页初始化完成")
    
    def _init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # ===== 频道URL输入区域 =====
        input_group = QGroupBox("频道链接")
        input_layout = QVBoxLayout(input_group)
        
        # URL 输入框
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入 YouTube 频道URL（格式：https://www.youtube.com/channel/CHANNEL_ID）")
        input_layout.addWidget(self.url_input)
        
        # 选项行
        options_layout = QHBoxLayout()
        
        self.use_cookie_checkbox = QCheckBox("使用 Cookie")
        self.use_cookie_checkbox.setToolTip("用于会员或年龄限制视频")
        options_layout.addWidget(self.use_cookie_checkbox)
        
        options_layout.addStretch()
        
        # 解析按钮
        self.parse_button = QPushButton("解析频道")
        self.parse_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
        self.parse_button.clicked.connect(self._on_parse_clicked)
        self.parse_button.setMinimumWidth(100)
        options_layout.addWidget(self.parse_button)
        
        input_layout.addLayout(options_layout)
        main_layout.addWidget(input_group)
        
        # ===== 频道信息显示区域 =====
        info_group = QGroupBox("频道信息")
        info_layout = QVBoxLayout(info_group)
        
        # 频道名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("频道名称:"))
        self.channel_name_label = QLabel("未解析")
        name_layout.addWidget(self.channel_name_label, 1)
        info_layout.addLayout(name_layout)
        
        # 视频数量
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("视频数量:"))
        self.video_count_label = QLabel("未解析")
        count_layout.addWidget(self.video_count_label)
        count_layout.addStretch()
        info_layout.addLayout(count_layout)
        
        main_layout.addWidget(info_group)
        
        # ===== 下载设置区域 =====
        settings_group = QGroupBox("下载设置")
        settings_layout = QVBoxLayout(settings_group)
        
        # 视频质量选择
        video_quality_layout = QHBoxLayout()
        video_quality_layout.addWidget(QLabel("视频质量:"))
        self.video_quality_combo = QComboBox()
        self.video_quality_combo.addItem("最高画质 (自动选择)", "best")
        self.video_quality_combo.setEnabled(True)
        video_quality_layout.addWidget(self.video_quality_combo)
        settings_layout.addLayout(video_quality_layout)
        
        # 音频质量选择
        audio_quality_layout = QHBoxLayout()
        audio_quality_layout.addWidget(QLabel("音频质量:"))
        self.audio_quality_combo = QComboBox()
        self.audio_quality_combo.addItem("最高音质 (自动选择)", "best")
        self.audio_quality_combo.setEnabled(True)
        audio_quality_layout.addWidget(self.audio_quality_combo)
        settings_layout.addLayout(audio_quality_layout)
        
        # 下载目录
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("下载目录:"))
        self.dir_input = QLineEdit()
        self.dir_input.setReadOnly(True)
        self.dir_input.setPlaceholderText("请选择下载目录")
        dir_layout.addWidget(self.dir_input, 1)
        self.browse_button = QPushButton("浏览")
        self.browse_button.clicked.connect(self._browse_download_dir)
        dir_layout.addWidget(self.browse_button)
        settings_layout.addLayout(dir_layout)
        
        main_layout.addWidget(settings_group)
        
        # ===== 进度显示区域 =====
        progress_group = QGroupBox("进度")
        progress_layout = QVBoxLayout(progress_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("准备就绪")
        progress_layout.addWidget(self.status_label)
        
        main_layout.addWidget(progress_group)
        
        # ===== 操作按钮区域 =====
        button_layout = QHBoxLayout()
        
        self.add_to_queue_button = QPushButton("添加到下载队列")
        self.add_to_queue_button.clicked.connect(self._on_add_to_queue_clicked)
        self.add_to_queue_button.setEnabled(False)
        button_layout.addWidget(self.add_to_queue_button)
        
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        # 添加弹性空间
        main_layout.addStretch()
    
    def _validate_channel_url(self, url: str) -> Tuple[bool, str]:
        """验证频道URL"""
        if not re.match(r'https?://', url):
            return False, "请输入有效的链接，应以 http:// 或 https:// 开头"
        
        if not self.video_info_parser.is_channel_url(url):
            return False, "请输入有效的频道URL（格式：https://www.youtube.com/channel/CHANNEL_ID 或 https://www.youtube.com/@USERNAME）"
        
        return True, ""
    
    def _on_parse_clicked(self):
        """解析按钮点击"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入频道URL")
            return
        
        # 验证URL
        is_valid, error_message = self._validate_channel_url(url)
        if not is_valid:
            QMessageBox.warning(self, "链接无效", error_message)
            return
        
        # 检查Cookie
        use_cookies = self.use_cookie_checkbox.isChecked()
        cookies_file = None
        if use_cookies:
            if not self.cookie_tab or not self.cookie_tab.is_cookie_available():
                reply = QMessageBox.question(
                    self, "Cookie 未设置",
                    "您选择了使用 Cookie，但当前没有可用的 Cookie。\n是否继续（不使用 Cookie）？",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
                use_cookies = False
                self.use_cookie_checkbox.setChecked(False)
            else:
                cookies_file = self.cookie_tab.get_cookie_file()
        
        # 禁用解析按钮
        self.parse_button.setEnabled(False)
        self.parse_button.setText("解析中...")
        self.status_label.setText("正在解析频道...")
        self.progress_bar.setValue(0)
        
        # 获取代理设置
        proxy_url = self._get_proxy_url()
        
        # 启动频道视频获取线程
        self.channel_thread = ChannelVideosThread(
            url, self.video_info_parser, use_cookies, cookies_file, proxy_url
        )
        self.channel_thread.channel_info_retrieved.connect(self._on_channel_info_retrieved)
        self.channel_thread.videos_retrieved.connect(self._on_videos_retrieved)
        self.channel_thread.progress_updated.connect(self._on_progress_updated)
        self.channel_thread.error_occurred.connect(self._on_error_occurred)
        self.channel_thread.start()
    
    def _on_channel_info_retrieved(self, channel_info: Dict):
        """频道信息获取成功"""
        self.channel_info = channel_info
        self.channel_name_label.setText(channel_info.get('uploader', '未知频道'))
        self.video_count_label.setText(str(channel_info.get('video_count', 0)))
    
    def _on_videos_retrieved(self, videos: List[Dict]):
        """视频列表获取成功"""
        self.channel_videos = videos
        self.parse_button.setEnabled(True)
        self.parse_button.setText("解析频道")
        self.status_label.setText(f"解析完成，共找到 {len(videos)} 个视频")
        self.progress_bar.setValue(100)
        self.add_to_queue_button.setEnabled(True)
        
        if self.status_bar:
            self.status_bar.showMessage(f"频道解析完成，共 {len(videos)} 个视频")
    
    def _on_progress_updated(self, current: int, total: int, status: str):
        """进度更新"""
        if self.status_bar:
            self.status_bar.showMessage(status)
        self.status_label.setText(status)
    
    def _on_error_occurred(self, error_message: str):
        """错误发生"""
        self.parse_button.setEnabled(True)
        self.parse_button.setText("解析频道")
        self.status_label.setText("解析失败")
        self.progress_bar.setValue(0)
        
        formatted_message = ErrorMessages.get_user_message(error_message, include_suggestion=True)
        QMessageBox.critical(self, "解析失败", formatted_message)
        
        if self.status_bar:
            self.status_bar.showMessage("频道解析失败")
    
    def _on_add_to_queue_clicked(self):
        """添加到下载队列按钮点击"""
        if not self.channel_videos:
            QMessageBox.warning(self, "警告", "没有可下载的视频")
            return
        
        # 检查下载目录
        output_dir = self.dir_input.text()
        if not output_dir:
            QMessageBox.warning(self, "警告", "请先选择下载目录")
            return
        
        # 获取选择的格式
        video_format_id = self.video_quality_combo.currentData()
        audio_format_id = self.audio_quality_combo.currentData()
        
        use_cookies = self.use_cookie_checkbox.isChecked()
        cookies_file = self.cookie_tab.get_cookie_file() if use_cookies and self.cookie_tab and self.cookie_tab.is_cookie_available() else None
        proxy_url = self._get_proxy_url()
        
        # 询问用户确认
        reply = QMessageBox.question(
            self, "确认",
            f"确定要将 {len(self.channel_videos)} 个视频添加到下载队列吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 切换到多视频下载标签页并添加任务
        main_window = self.window()
        if main_window and hasattr(main_window, 'multi_download_tab'):
            # 将视频URL添加到多视频下载标签页的输入框
            video_urls = '\n'.join([video['url'] for video in self.channel_videos])
            main_window.multi_download_tab.url_input.setPlainText(video_urls)
            
            # 切换到多视频下载标签页
            main_window.tab_widget.setCurrentWidget(main_window.multi_download_tab)
            
            # 提示用户
            QMessageBox.information(
                self, "已添加",
                f"已将 {len(self.channel_videos)} 个视频添加到多视频下载标签页。\n请在多视频下载标签页中点击\"解析链接\"按钮继续。"
            )
        else:
            QMessageBox.warning(self, "错误", "无法访问多视频下载标签页")
    
    def _browse_download_dir(self):
        """浏览下载目录"""
        current_dir = self.dir_input.text() or os.path.expanduser("~/Desktop")
        
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择下载文件夹", current_dir
        )
        
        if dir_path:
            self.dir_input.setText(dir_path)
            if self.config_manager:
                self.config_manager.set('download_dir', dir_path)
    
    def _set_default_download_dir(self):
        """设置默认下载目录"""
        if self.config_manager:
            last_dir = self.config_manager.get('download_dir')
            if last_dir and os.path.exists(last_dir):
                self.dir_input.setText(last_dir)
                return
        
        # 使用桌面作为默认目录
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        if os.path.exists(desktop):
            self.dir_input.setText(desktop)
    
    def _get_proxy_url(self) -> Optional[str]:
        """
        从配置中获取代理URL
        
        Returns:
            代理URL，如果未启用代理则返回None
        """
        if not self.config_manager.get('proxy_enabled', False):
            return None
        
        proxy_type = self.config_manager.get('proxy_type', 'http')
        proxy_host = self.config_manager.get('proxy_host', '127.0.0.1')
        proxy_port = self.config_manager.get('proxy_port', 7890)
        proxy_username = self.config_manager.get('proxy_username', '')
        proxy_password = self.config_manager.get('proxy_password', '')
        
        if not proxy_host:
            return None
        
        # 构建代理URL
        if proxy_username and proxy_password:
            return f"{proxy_type}://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
        else:
            return f"{proxy_type}://{proxy_host}:{proxy_port}"

