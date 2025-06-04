"""
YouTube Downloader 下载标签页模块
负责创建和管理下载标签页界面
"""
import os
import sys
import threading
from typing import Optional, List, Dict, Tuple

# 导入 PyQt5 模块
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTextEdit,
    QProgressBar, QFileDialog, QRadioButton, QComboBox, QMessageBox, QGroupBox,
    QSplitter, QFrame, QApplication, QDialog, QStatusBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QIcon, QFont, QPixmap, QCursor

# 导入自定义模块
from src.core.downloader import VideoDownloader
from src.core.cookie_manager import CookieManager
from src.core.format_converter import FormatConverter
from src.utils.notification import NotificationManager
from src.utils.config import ConfigManager
from src.utils.logger import LoggerManager
from src.core.video_info.video_info_parser import VideoInfoParser


class CookieExtractorThread(QThread):
    """Cookie提取线程类"""
    
    # 定义信号
    extraction_completed = pyqtSignal(bool, str, str)
    
    def __init__(self, cookie_manager: CookieManager):
        """
        初始化Cookie提取线程
        
        Args:
            cookie_manager: Cookie管理器
        """
        super().__init__()
        self.cookie_manager = cookie_manager
    
    def run(self):
        """执行Cookie提取任务"""
        try:
            success, temp_cookie_file, error_message = self.cookie_manager.auto_extract_cookies()
            self.extraction_completed.emit(success, temp_cookie_file, error_message)
        except Exception as e:
            self.extraction_completed.emit(False, "", str(e))


class VideoInfoThread(QThread):
    """视频信息获取线程类"""
    
    # 定义信号
    info_retrieved = pyqtSignal(dict)  # 视频信息信号
    error_occurred = pyqtSignal(str)   # 错误信号
    progress_updated = pyqtSignal(str) # 进度信号
    
    def __init__(self, video_info_parser: VideoInfoParser, url: str, use_cookies: bool = False, cookies_file: str = None):
        """
        初始化视频信息获取线程
        
        Args:
            video_info_parser: 视频信息解析器
            url: 视频URL
            use_cookies: 是否使用cookies
            cookies_file: cookies文件路径
        """
        super().__init__()
        self.video_info_parser = video_info_parser
        self.url = url
        self.use_cookies = use_cookies
        self.cookies_file = cookies_file
    
    def run(self):
        """执行视频信息获取任务"""
        try:
            # 发送进度信号
            self.progress_updated.emit("正在获取视频基本信息...")
            
            # 获取视频信息
            video_info = self.video_info_parser.parse_video(self.url)
            
            # 发送信号
            self.info_retrieved.emit(video_info)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class DownloadThread(QThread):
    """下载线程"""
    progress_updated = pyqtSignal(float, str, str)  # 进度、速度、剩余时间信号
    status_updated = pyqtSignal(str)    # 状态信号
    download_completed = pyqtSignal()   # 完成信号
    download_error = pyqtSignal(str)    # 错误信号
    
    def __init__(self, downloader: VideoDownloader, url: str, output_dir: str, 
                 video_format_id: str, audio_format_id: str, use_cookies: bool = False, 
                 cookies_file: str = None, prefer_mp4: bool = True):
        super().__init__()
        self.downloader = downloader
        self.url = url
        self.output_dir = output_dir
        self.video_format_id = video_format_id
        self.audio_format_id = audio_format_id
        self.use_cookies = use_cookies
        self.cookies_file = cookies_file
        self.prefer_mp4 = prefer_mp4
        self.is_cancelled = False
        self.logger = LoggerManager().get_logger()
    
    def run(self):
        """运行下载线程"""
        try:
            # 设置回调函数
            self.downloader.set_callbacks(
                progress_callback=self._progress_callback,
                completion_callback=self._completion_callback,
                error_callback=self._error_callback
            )
            
            # 开始下载
            self.downloader.download_videos(
                urls=[self.url],  # 将单个URL包装成列表
                output_dir=self.output_dir,
                format_id=f"{self.video_format_id}+{self.audio_format_id}" if self.audio_format_id else self.video_format_id,
                use_cookies=self.use_cookies,
                cookies_file=self.cookies_file,
                prefer_mp4=self.prefer_mp4
            )
            
        except Exception as e:
            self.download_error.emit(str(e))
    
    def _progress_callback(self, progress: float, speed: str, eta: str, video_title: str, video_index: int, total_videos: int):
        """进度回调函数"""
        try:
            # 更新进度条
            self.progress_updated.emit(progress, speed, eta)
            
            # 更新状态信息：显示下载速度和剩余时间
            status = f"下载中... {speed} - 剩余时间: {eta}"
            self.status_updated.emit(status)
            
        except Exception as e:
            self.logger.error(f"处理进度信息时出错: {str(e)}")
            self.progress_updated.emit(0.0, "0 KiB/s", "00:00")
            self.status_updated.emit("下载出错")
    
    def _completion_callback(self, success: bool, output_dir: str, error_message: str = None):
        """完成回调函数"""
        if success:
            self.download_completed.emit()
        elif error_message == "下载已取消":
            # 取消下载的情况
            self.is_cancelled = True
            self.download_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.status_label.setText("下载已取消")
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("%p%")  # 重置进度条格式
            QMessageBox.information(self, "提示", "下载已取消")
        else:
            # 真正的下载失败
            self.download_error.emit(error_message or "下载失败")
    
    def _error_callback(self, error_message: str):
        """错误回调函数"""
        self.download_error.emit(error_message)
    
    def cancel(self):
        """取消下载"""
        self.is_cancelled = True
        self.downloader.cancel_download()


class DownloadTab(QWidget):
    """下载标签页类"""
    
    def __init__(self, config_manager: ConfigManager, status_bar: QStatusBar = None, cookie_tab = None):
        """
        初始化下载标签页
        
        Args:
            config_manager: 配置管理器
            status_bar: 状态栏
            cookie_tab: Cookie标签页实例
        """
        super().__init__()
        
        # 初始化日志和配置
        self.logger = LoggerManager().get_logger()
        self.config_manager = config_manager
        self.status_bar = status_bar
        self.cookie_tab = cookie_tab
        
        # 初始化核心组件
        self.downloader = VideoDownloader()
        self.cookie_manager = CookieManager()
        self.format_converter = FormatConverter()
        self.video_info_parser = VideoInfoParser()
        self.notification_manager = NotificationManager()
        
        # 下载状态
        self.is_downloading = False
        self.download_thread = None
        self.video_info_thread = None
        self.cookie_extractor_thread = None
        self.current_url = ""
        
        # 初始化 UI
        self.init_ui()
        
        # 设置默认下载目录
        self.set_default_download_dir()
        
        # 记录日志
        self.logger.info("下载标签页初始化完成")
    
    def init_ui(self):
        """初始化 UI"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 创建输入区域
        input_group = QGroupBox("视频链接")
        input_layout = QVBoxLayout(input_group)
        
        # 视频链接输入框
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("在此输入YouTube 视频链接。")
        self.url_input.setMinimumHeight(80)
        input_layout.addWidget(self.url_input)
        
        # 解析按钮
        parse_layout = QHBoxLayout()
        self.parse_button = QPushButton("解析视频信息")
        self.parse_button.clicked.connect(self.parse_video_info)
        parse_layout.addStretch()
        parse_layout.addWidget(self.parse_button)
        input_layout.addLayout(parse_layout)
        
        # 添加输入区域到主布局
        main_layout.addWidget(input_group)
        
        # 创建视频信息区域
        info_group = QGroupBox("视频信息")
        info_layout = QVBoxLayout(info_group)
        
        # 视频标题
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("标题:"))
        self.title_label = QLabel("未解析")
        self.title_label.setWordWrap(True)
        title_layout.addWidget(self.title_label, 1)
        info_layout.addLayout(title_layout)
        
        # 视频时长
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("时长:"))
        self.duration_label = QLabel("未解析")
        duration_layout.addWidget(self.duration_label)
        duration_layout.addStretch()
        info_layout.addLayout(duration_layout)
        
        # 添加视频信息区域到主布局
        main_layout.addWidget(info_group)
        
        # 创建下载选项区域
        options_group = QGroupBox("下载选项")
        options_layout = QVBoxLayout(options_group)
        
        # 视频质量选择
        video_quality_layout = QHBoxLayout()
        video_quality_layout.addWidget(QLabel("视频质量:"))
        self.video_quality_combo = QComboBox()
        self.video_quality_combo.setEnabled(False)
        video_quality_layout.addWidget(self.video_quality_combo)
        options_layout.addLayout(video_quality_layout)
        
        # 音频质量选择
        audio_quality_layout = QHBoxLayout()
        audio_quality_layout.addWidget(QLabel("音频质量:"))
        self.audio_quality_combo = QComboBox()
        self.audio_quality_combo.setEnabled(False)
        audio_quality_layout.addWidget(self.audio_quality_combo)
        options_layout.addLayout(audio_quality_layout)
        
        # Cookie选项
        cookie_layout = QHBoxLayout()
        self.use_cookie_checkbox = QRadioButton("使用Cookie")
        self.use_cookie_checkbox.setChecked(False)
        cookie_layout.addWidget(self.use_cookie_checkbox)
        cookie_layout.addStretch()
        options_layout.addLayout(cookie_layout)
        
        # 下载目录选择
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
        
        # 添加下载选项区域到主布局
        main_layout.addWidget(options_group)
        
        # 创建下载进度区域
        progress_group = QGroupBox("下载进度")
        progress_layout = QVBoxLayout(progress_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("准备就绪")
        progress_layout.addWidget(self.status_label)
        
        # 添加下载进度区域到主布局
        main_layout.addWidget(progress_group)
        
        # 创建按钮区域
        button_layout = QHBoxLayout()
        
        # 下载按钮
        self.download_button = QPushButton("开始下载")
        self.download_button.clicked.connect(self.start_download)
        self.download_button.setEnabled(False)
        button_layout.addWidget(self.download_button)
        
        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        
        # 添加按钮区域到主布局
        main_layout.addLayout(button_layout)
        
        # 添加弹性空间
        main_layout.addStretch()
        
        # 连接信号
        self.dir_input.textChanged.connect(self.check_download_button)
        
        # 初始检查下载按钮状态
        self.check_download_button()
    
    def check_download_button(self):
        """检查下载按钮状态"""
        # 如果下载路径不为空，则启用下载按钮
        self.download_button.setEnabled(
            bool(self.dir_input.text()) and not self.is_downloading
        )
    
    def update_status_message(self, message):
        """更新状态栏消息"""
        if self.status_bar:
            self.status_bar.showMessage(message)
    
    def parse_video_info(self):
        """解析视频信息"""
        # 获取视频链接
        url = self.url_input.toPlainText().strip()
        if not url:
            QMessageBox.warning(self, "错误", "请输入视频链接")
            return
            
        try:
            # 显示加载状态
            self.status_label.setText("正在解析视频信息...")
            self.parse_button.setEnabled(False)
            QApplication.processEvents()
            
            # 创建并启动视频信息获取线程
            self.video_info_thread = VideoInfoThread(
                self.video_info_parser, 
                url,
                use_cookies=self.use_cookie_checkbox.isChecked(),
                cookies_file=self.cookie_manager.get_cookie_file() if self.use_cookie_checkbox.isChecked() else None
            )
            self.video_info_thread.info_retrieved.connect(self.on_video_info_retrieved)
            self.video_info_thread.error_occurred.connect(self.on_video_info_error)
            self.video_info_thread.progress_updated.connect(self.update_status)
            self.video_info_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"解析视频信息失败：{str(e)}")
            self.status_label.setText("解析失败")
            self.parse_button.setEnabled(True)
    
    def on_video_info_retrieved(self, video_info: Dict):
        """视频信息获取成功回调"""
        try:
            # 更新视频信息显示
            self.title_label.setText(video_info['title'])
            self.duration_label.setText(self.video_info_parser.format_duration(video_info['duration']))
            
            # 获取可用格式
            formats = self.video_info_parser.get_available_formats(video_info)
            formatted_formats = self.video_info_parser.get_formatted_formats(formats)
            
            # 更新视频质量选项
            self.video_quality_combo.clear()
            self.video_quality_combo.setEnabled(True)
            
            # 添加最高画质选项
            self.video_quality_combo.addItem("最高画质 (自动选择)", "best")
            
            # 添加视频格式选项
            for fmt in formatted_formats:
                if fmt['type'] == 'video':
                    self.video_quality_combo.addItem(fmt['display'], fmt['format_id'])
            
            # 更新音频质量选项
            self.audio_quality_combo.clear()
            self.audio_quality_combo.setEnabled(True)
            
            # 添加最高音质选项
            self.audio_quality_combo.addItem("最高音质 (自动选择)", "best")
            
            # 添加音频格式选项
            for fmt in formatted_formats:
                if fmt['type'] == 'audio':
                    self.audio_quality_combo.addItem(fmt['display'], fmt['format_id'])
            
            # 更新状态
            self.status_label.setText("视频信息解析完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理视频信息失败：{str(e)}")
            self.status_label.setText("解析失败")
            
        finally:
            self.parse_button.setEnabled(True)
    
    def on_video_info_error(self, error_message: str):
        """视频信息获取失败回调"""
        QMessageBox.critical(self, "错误", f"解析视频信息失败：{error_message}")
        self.status_label.setText("解析失败")
        self.parse_button.setEnabled(True)
    
    def start_download(self):
        """开始下载视频"""
        # 获取视频链接
        url = self.url_input.toPlainText().strip()
        if not url:
            QMessageBox.warning(self, "错误", "请输入视频链接")
            return
            
        # 获取下载路径
        output_dir = self.dir_input.text()
        if not output_dir:
            QMessageBox.warning(self, "错误", "请选择下载目录")
            return
            
        # 获取选择的视频和音频格式
        video_format_id = self.video_quality_combo.currentData()
        audio_format_id = self.audio_quality_combo.currentData()
        
        try:
            # 更新UI状态
            self.is_downloading = True
            self.download_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.status_label.setText("正在准备下载...")
            self.progress_bar.setValue(0)
            
            # 创建下载线程
            self.download_thread = DownloadThread(
                downloader=self.downloader,
                url=url,
                output_dir=output_dir,
                video_format_id=video_format_id,
                audio_format_id=audio_format_id,
                use_cookies=self.use_cookie_checkbox.isChecked(),
                cookies_file=self.cookie_manager.get_cookie_file() if self.use_cookie_checkbox.isChecked() else None,
                prefer_mp4=True  # 默认优先选择MP4格式
            )
            
            # 连接信号
            self.download_thread.progress_updated.connect(self.update_progress)
            self.download_thread.status_updated.connect(self.update_status)
            self.download_thread.download_completed.connect(self.on_download_completed)
            self.download_thread.download_error.connect(self.on_download_error)
            
            # 启动下载线程
            self.download_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动下载失败：{str(e)}")
            self.on_download_error(str(e))
    
    def update_progress(self, progress: float, speed: str, eta: str):
        """更新下载进度"""
        self.progress_bar.setValue(int(progress))
        self.status_label.setText(f"下载中... {progress:.1f}% - {speed} - 剩余时间: {eta}")
    
    def update_status(self, status: str):
        """更新下载状态"""
        self.status_label.setText(status)
    
    def on_download_completed(self):
        """下载完成回调"""
        self.is_downloading = False
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status_label.setText("下载完成")
        QMessageBox.information(self, "完成", "视频下载完成！")
    
    def on_download_error(self, error_message: str):
        """下载错误回调"""
        self.is_downloading = False
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status_label.setText("下载失败")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")  # 重置进度条格式
        QMessageBox.critical(self, "错误", f"下载失败：{error_message}")
    
    def cancel_download(self):
        """取消下载"""
        if not self.is_downloading or not self.download_thread:
            return
            
        try:
            # 更新UI状态
            self.status_label.setText("正在取消下载...")
            self.cancel_button.setEnabled(False)
            
            # 取消下载
            self.download_thread.cancel()
            
            # 等待下载线程结束
            self.download_thread.wait()
            
        except Exception as e:
            self.logger.error(f"取消下载时出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"取消下载失败: {str(e)}")
            self.on_download_error("取消下载失败")
    
    def set_default_download_dir(self):
        """设置默认下载目录"""
        # 获取上次使用的下载目录
        last_dir = self.config_manager.get('download_dir')
        
        # 如果没有上次使用的目录，则使用桌面作为默认目录
        if not last_dir:
            last_dir = os.path.join(os.path.expanduser('~'), 'Desktop')
            
        # 确保目录存在
        if not os.path.exists(last_dir):
            last_dir = os.path.join(os.path.expanduser('~'), 'Desktop')
            
        # 设置下载目录
        self.dir_input.setText(last_dir)
        self.config_manager.set('download_dir', last_dir)
    
    def browse_download_dir(self):
        """浏览下载目录"""
        # 获取当前目录或默认目录
        current_dir = self.dir_input.text() or os.path.join(os.path.expanduser('~'), 'Desktop')
        
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择下载文件夹",
            current_dir
        )
        
        if dir_path:
            self.dir_input.setText(dir_path)
            self.config_manager.set('download_dir', dir_path)
