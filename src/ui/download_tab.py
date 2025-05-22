"""
YouTube 视频下载工具的下载标签页模块
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


class DownloadWorker(QThread):
    """下载工作线程类"""
    
    # 定义信号
    progress_updated = pyqtSignal(float, str, str, str, int, int)
    download_completed = pyqtSignal(bool, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, downloader: VideoDownloader, urls: List[str], output_dir: str,
                 format_id: str, use_cookies: bool, cookies_file: str, prefer_mp4: bool):
        """
        初始化下载工作线程
        
        Args:
            downloader: 视频下载器
            urls: 视频URL列表
            output_dir: 输出目录
            format_id: 格式ID
            use_cookies: 是否使用cookies
            cookies_file: cookies文件路径
            prefer_mp4: 是否优先选择MP4格式
        """
        super().__init__()
        self.downloader = downloader
        self.urls = urls
        self.output_dir = output_dir
        self.format_id = format_id
        self.use_cookies = use_cookies
        self.cookies_file = cookies_file
        self.prefer_mp4 = prefer_mp4
    
    def run(self):
        """执行下载任务"""
        # 设置回调函数
        self.downloader.set_callbacks(
            progress_callback=self._progress_callback,
            completion_callback=self._completion_callback,
            error_callback=self._error_callback
        )
        
        # 开始下载
        self.downloader.download_videos(
            urls=self.urls,
            output_dir=self.output_dir,
            format_id=self.format_id,
            use_cookies=self.use_cookies,
            cookies_file=self.cookies_file,
            prefer_mp4=self.prefer_mp4
        )
    
    def _progress_callback(self, progress: float, speed: str, eta: str, title: str, current_index: int, total_videos: int):
        """进度回调函数"""
        self.progress_updated.emit(progress, speed, eta, title, current_index, total_videos)
    
    def _completion_callback(self, success: bool, output_dir: str):
        """完成回调函数"""
        self.download_completed.emit(success, output_dir)
    
    def _error_callback(self, error_message: str):
        """错误回调函数"""
        self.error_occurred.emit(error_message)


class VideoInfoThread(QThread):
    """视频信息获取线程类"""
    
    # 定义信号
    info_retrieved = pyqtSignal(object, list)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(str)
    
    def __init__(self, downloader: VideoDownloader, url: str, use_cookies: bool, cookies_file: str):
        """
        初始化视频信息获取线程
        
        Args:
            downloader: 视频下载器
            url: 视频URL
            use_cookies: 是否使用cookies
            cookies_file: cookies文件路径
        """
        super().__init__()
        self.downloader = downloader
        self.url = url
        self.use_cookies = use_cookies
        self.cookies_file = cookies_file
    
    def run(self):
        """执行视频信息获取任务"""
        try:
            # 发送进度信号
            self.progress_updated.emit("正在获取视频基本信息...")
            
            # 获取视频信息
            video_info = self.downloader.extract_video_info(self.url, self.use_cookies, self.cookies_file)
            
            # 发送进度信号
            self.progress_updated.emit("正在获取可用格式列表...")
            
            # 获取可用格式
            available_formats = self.downloader.get_available_formats(self.url, self.use_cookies, self.cookies_file)
            
            # 发送信号
            self.info_retrieved.emit(video_info, available_formats)
        except Exception as e:
            self.error_occurred.emit(str(e))


class DownloadTab(QWidget):
    """下载标签页类"""
    
    def __init__(self, config_manager: ConfigManager, status_bar: QStatusBar = None):
        """
        初始化下载标签页
        
        Args:
            config_manager: 配置管理器
            status_bar: 状态栏
        """
        super().__init__()
        
        # 初始化日志和配置
        self.logger = LoggerManager().get_logger()
        self.config_manager = config_manager
        self.status_bar = status_bar
        
        # 初始化核心组件
        self.downloader = VideoDownloader()
        self.cookie_manager = CookieManager()
        self.format_converter = FormatConverter()
        self.notification_manager = NotificationManager()
        
        # 下载状态
        self.is_downloading = False
        self.download_worker = None
        self.video_info_thread = None
        self.cookie_extractor_thread = None
        self.available_formats = []
        self.current_url = ""
        
        # 初始化 UI
        self.init_ui()
        
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
        self.url_input.setPlaceholderText("在此输入一个或多个 YouTube 视频链接，每行一个")
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
        
        # Cookie 选项
        cookie_group = QGroupBox("Cookie 设置")
        cookie_layout = QVBoxLayout(cookie_group)
        
        # 不使用 Cookie 选项
        self.no_cookie_radio = QRadioButton("不使用 Cookie")
        self.no_cookie_radio.setChecked(not self.config_manager.get('use_cookies', True))
        self.no_cookie_radio.toggled.connect(self.toggle_cookie_mode)
        cookie_layout.addWidget(self.no_cookie_radio)
        
        # 自动获取 Cookie 选项
        self.auto_cookie_radio = QRadioButton("自动从浏览器获取 Cookie")
        self.auto_cookie_radio.setChecked(self.config_manager.get('auto_cookies', True) and self.config_manager.get('use_cookies', True))
        self.auto_cookie_radio.toggled.connect(self.toggle_cookie_mode)
        cookie_layout.addWidget(self.auto_cookie_radio)
        
        # 手动导入 Cookie 选项
        self.manual_cookie_radio = QRadioButton("手动导入 Cookie 文件")
        self.manual_cookie_radio.setChecked(not self.config_manager.get('auto_cookies', True) and self.config_manager.get('use_cookies', True))
        cookie_layout.addWidget(self.manual_cookie_radio)
        
        # Cookie 文件路径
        cookie_file_layout = QHBoxLayout()
        self.cookie_file_input = QLineEdit()
        self.cookie_file_input.setPlaceholderText("Cookie 文件路径")
        self.cookie_file_input.setText(self.config_manager.get('cookies_file', ''))
        self.cookie_file_input.setEnabled(not self.config_manager.get('auto_cookies', True) and self.config_manager.get('use_cookies', True))
        cookie_file_layout.addWidget(self.cookie_file_input)
        
        # 浏览按钮
        self.browse_cookie_button = QPushButton("浏览...")
        self.browse_cookie_button.clicked.connect(self.browse_cookie_file)
        self.browse_cookie_button.setEnabled(not self.config_manager.get('auto_cookies', True) and self.config_manager.get('use_cookies', True))
        cookie_file_layout.addWidget(self.browse_cookie_button)
        
        cookie_layout.addLayout(cookie_file_layout)
        options_layout.addWidget(cookie_group)
        
        # 下载位置选项
        location_group = QGroupBox("下载位置")
        location_layout = QHBoxLayout(location_group)
        
        # 下载路径输入框
        self.download_dir_input = QLineEdit()
        self.download_dir_input.setPlaceholderText("选择下载文件夹")
        self.download_dir_input.setText(self.config_manager.get('download_dir', ''))
        location_layout.addWidget(self.download_dir_input)
        
        # 浏览按钮
        self.browse_dir_button = QPushButton("浏览...")
        self.browse_dir_button.clicked.connect(self.browse_download_dir)
        location_layout.addWidget(self.browse_dir_button)
        
        options_layout.addWidget(location_group)
        
        # 视频质量选项
        quality_group = QGroupBox("视频质量")
        quality_layout = QVBoxLayout(quality_group)
        
        # 清晰度下拉选择框
        quality_layout.addWidget(QLabel("选择清晰度:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItem("最高画质 (自动选择)", "best")
        quality_layout.addWidget(self.quality_combo)
        
        # MP4 优先选项
        self.mp4_checkbox = QRadioButton("优先选择 MP4 格式 (需要时自动转换)")
        self.mp4_checkbox.setChecked(self.config_manager.get('prefer_mp4', True))
        quality_layout.addWidget(self.mp4_checkbox)
        
        options_layout.addWidget(quality_group)
        
        # 添加下载选项区域到主布局
        main_layout.addWidget(options_group)
        
        # 创建下载控制区域
        control_group = QGroupBox("下载控制")
        control_layout = QVBoxLayout(control_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        control_layout.addWidget(self.progress_bar)
        
        # 下载信息
        info_layout = QHBoxLayout()
        self.speed_label = QLabel("速度: 0 KiB/s")
        info_layout.addWidget(self.speed_label)
        self.eta_label = QLabel("剩余时间: 00:00")
        info_layout.addWidget(self.eta_label)
        self.video_count_label = QLabel("0/0")
        info_layout.addWidget(self.video_count_label)
        control_layout.addLayout(info_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 下载按钮
        self.download_button = QPushButton("开始下载")
        self.download_button.clicked.connect(self.start_download)
        self.download_button.setEnabled(False)  # 初始禁用，直到选择下载路径
        button_layout.addWidget(self.download_button)
        
        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        
        control_layout.addLayout(button_layout)
        
        # 添加下载控制区域到主布局
        main_layout.addWidget(control_group)
        
        # 添加弹性空间
        main_layout.addStretch()
        
        # 连接信号
        self.download_dir_input.textChanged.connect(self.check_download_button)
        
        # 初始检查下载按钮状态
        self.check_download_button()
    
    def toggle_cookie_mode(self, checked):
        """切换 Cookie 模式"""
        if self.no_cookie_radio.isChecked():
            self.cookie_file_input.setEnabled(False)
            self.browse_cookie_button.setEnabled(False)
            self.config_manager.set('use_cookies', False)
        elif self.auto_cookie_radio.isChecked():
            self.cookie_file_input.setEnabled(False)
            self.browse_cookie_button.setEnabled(False)
            self.config_manager.set('use_cookies', True)
            self.config_manager.set('auto_cookies', True)
        else:  # 手动模式
            self.cookie_file_input.setEnabled(True)
            self.browse_cookie_button.setEnabled(True)
            self.config_manager.set('use_cookies', True)
            self.config_manager.set('auto_cookies', False)
    
    def browse_cookie_file(self):
        """浏览 Cookie 文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 Cookie 文件",
            "",
            "Cookie 文件 (*.txt);;所有文件 (*.*)"
        )
        
        if file_path:
            self.cookie_file_input.setText(file_path)
            self.config_manager.set('cookies_file', file_path)
    
    def browse_download_dir(self):
        """浏览下载目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择下载文件夹",
            self.download_dir_input.text()
        )
        
        if dir_path:
            self.download_dir_input.setText(dir_path)
            self.config_manager.set('download_dir', dir_path)
    
    def check_download_button(self):
        """检查下载按钮状态"""
        # 如果下载路径不为空，则启用下载按钮
        self.download_button.setEnabled(
            bool(self.download_dir_input.text()) and not self.is_downloading
        )
    
    def update_status_message(self, message):
        """更新状态栏消息"""
        if self.status_bar:
            self.status_bar.showMessage(message, 5000)  # 显示5秒
    
    def parse_video_info(self):
        """解析视频信息"""
        # 获取URL
        urls_text = self.url_input.toPlainText().strip()
        if not urls_text:
            QMessageBox.warning(self, "错误", "请输入至少一个视频链接")
            return
        
        # 分割多个URL
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        if not urls:
            QMessageBox.warning(self, "错误", "请输入有效的视频链接")
            return
        
        # 只解析第一个URL的信息
        self.current_url = urls[0]
        
        # 禁用解析按钮，防止重复点击
        self.parse_button.setEnabled(False)
        self.parse_button.setText("正在解析...")
        
        # 更新状态栏
        self.update_status_message("正在准备解析视频信息...")
        
        # 获取 Cookie 设置
        use_cookies = self.config_manager.get('use_cookies', True)
        auto_cookies = self.auto_cookie_radio.isChecked()
        cookies_file = self.cookie_file_input.text() if not auto_cookies else ""
        
        # 如果使用自动 Cookie 但尚未获取
        if use_cookies and auto_cookies and not cookies_file:
            # 更新状态栏
            self.update_status_message("正在从浏览器获取Cookie...")
            
            # 创建并启动Cookie提取线程
            self.cookie_extractor_thread = CookieExtractorThread(self.cookie_manager)
            self.cookie_extractor_thread.extraction_completed.connect(self.on_cookie_extraction_completed)
            self.cookie_extractor_thread.start()
        else:
            # 直接开始解析视频信息
            self.start_video_info_parsing(use_cookies, cookies_file)
    
    def on_cookie_extraction_completed(self, success, temp_cookie_file, error_message):
        """Cookie提取完成回调"""
        use_cookies = self.config_manager.get('use_cookies', True)
        
        if success:
            cookies_file = temp_cookie_file
            self.update_status_message("Cookie获取成功，正在解析视频...")
        else:
            QMessageBox.warning(self, "警告", f"无法自动获取 Cookie: {error_message}\n将尝试不使用 Cookie 下载")
            use_cookies = False
            cookies_file = ""
            self.update_status_message("Cookie获取失败，尝试不使用Cookie解析...")
        
        # 开始解析视频信息
        self.start_video_info_parsing(use_cookies, cookies_file)
    
    def start_video_info_parsing(self, use_cookies, cookies_file):
        """开始解析视频信息"""
        # 显示正在解析
        self.title_label.setText("正在解析...")
        self.duration_label.setText("正在解析...")
        
        # 更新状态栏
        self.update_status_message("正在解析视频信息...")
        
        # 创建并启动视频信息获取线程
        self.video_info_thread = VideoInfoThread(
            downloader=self.downloader,
            url=self.current_url,
            use_cookies=use_cookies,
            cookies_file=cookies_file
        )
        
        # 连接信号
        self.video_info_thread.info_retrieved.connect(self.on_video_info_retrieved)
        self.video_info_thread.error_occurred.connect(self.on_video_info_error)
        self.video_info_thread.progress_updated.connect(self.update_status_message)
        
        # 启动线程
        self.video_info_thread.start()
    
    def on_video_info_retrieved(self, video_info, available_formats):
        """视频信息获取完成回调"""
        # 保存可用格式
        self.available_formats = available_formats
        
        if video_info:
            # 更新视频标题
            self.title_label.setText(video_info.get('title', '未知标题'))
            
            # 更新视频时长
            duration_seconds = video_info.get('duration', 0)
            if duration_seconds:
                minutes, seconds = divmod(int(duration_seconds), 60)
                hours, minutes = divmod(minutes, 60)
                if hours > 0:
                    duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    duration_str = f"{minutes}:{seconds:02d}"
                self.duration_label.setText(duration_str)
            else:
                self.duration_label.setText("未知时长")
            
            # 更新清晰度选项
            self.quality_combo.clear()
            self.quality_combo.addItem("最高画质 (自动选择)", "best")
            
            for fmt in self.available_formats:
                label = self.format_converter.format_quality_label(fmt)
                self.quality_combo.addItem(label, fmt['format_id'])
            
            # 更新状态栏
            self.update_status_message("视频信息解析完成")
        else:
            self.title_label.setText("无法获取视频信息")
            self.duration_label.setText("未知")
            self.update_status_message("无法获取视频信息")
        
        # 恢复解析按钮
        self.parse_button.setEnabled(True)
        self.parse_button.setText("解析视频信息")
    
    def on_video_info_error(self, error_message):
        """视频信息获取错误回调"""
        QMessageBox.critical(self, "错误", f"解析视频信息失败: {error_message}")
        self.title_label.setText("解析失败")
        self.duration_label.setText("未知")
        
        # 恢复解析按钮
        self.parse_button.setEnabled(True)
        self.parse_button.setText("解析视频信息")
        
        # 更新状态栏
        self.update_status_message(f"解析失败: {error_message}")
        
        # 记录日志
        self.logger.error(f"解析视频信息时发生错误: {error_message}")
    
    def start_download(self):
        """开始下载"""
        # 检查是否已在下载
        if self.is_downloading:
            return
        
        # 获取URL
        urls_text = self.url_input.toPlainText().strip()
        if not urls_text:
            QMessageBox.warning(self, "错误", "请输入至少一个视频链接")
            return
        
        # 分割多个URL
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        if not urls:
            QMessageBox.warning(self, "错误", "请输入有效的视频链接")
            return
        
        # 获取下载路径
        output_dir = self.download_dir_input.text()
        if not output_dir:
            QMessageBox.warning(self, "错误", "请选择下载文件夹")
            return
        
        # 确保下载路径存在
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建下载文件夹失败: {str(e)}")
            return
        
        # 获取选择的格式
        format_id = self.quality_combo.currentData()
        
        # 获取 Cookie 设置
        use_cookies = self.config_manager.get('use_cookies', True)
        auto_cookies = self.auto_cookie_radio.isChecked()
        cookies_file = self.cookie_file_input.text() if not auto_cookies else ""
        
        # 如果使用自动 Cookie 但尚未获取
        if use_cookies and auto_cookies and not cookies_file:
            # 更新状态栏
            self.update_status_message("正在从浏览器获取Cookie...")
            
            # 显示等待光标
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            # 创建并启动Cookie提取线程
            self.cookie_extractor_thread = CookieExtractorThread(self.cookie_manager)
            self.cookie_extractor_thread.extraction_completed.connect(self.on_cookie_extraction_for_download_completed)
            self.cookie_extractor_thread.start()
        else:
            # 直接开始下载
            self.start_download_process(urls, output_dir, format_id, use_cookies, cookies_file)
    
    def on_cookie_extraction_for_download_completed(self, success, temp_cookie_file, error_message):
        """下载前Cookie提取完成回调"""
        # 恢复正常光标
        QApplication.restoreOverrideCursor()
        
        use_cookies = self.config_manager.get('use_cookies', True)
        
        if success:
            cookies_file = temp_cookie_file
            self.update_status_message("Cookie获取成功，开始下载...")
        else:
            QMessageBox.warning(self, "警告", f"无法自动获取 Cookie: {error_message}\n将尝试不使用 Cookie 下载")
            use_cookies = False
            cookies_file = ""
            self.update_status_message("Cookie获取失败，尝试不使用Cookie下载...")
        
        # 获取下载参数
        urls = [url.strip() for url in self.url_input.toPlainText().strip().split('\n') if url.strip()]
        output_dir = self.download_dir_input.text()
        format_id = self.quality_combo.currentData()
        
        # 开始下载
        self.start_download_process(urls, output_dir, format_id, use_cookies, cookies_file)
    
    def start_download_process(self, urls, output_dir, format_id, use_cookies, cookies_file):
        """开始下载流程"""
        # 获取 MP4 优先设置
        prefer_mp4 = self.mp4_checkbox.isChecked()
        
        # 更新 UI
        self.is_downloading = True
        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.speed_label.setText("速度: 0 KiB/s")
        self.eta_label.setText("剩余时间: 00:00")
        self.video_count_label.setText(f"0/{len(urls)}")
        
        # 更新状态栏
        self.update_status_message(f"开始下载 {len(urls)} 个视频...")
        
        # 创建并启动下载工作线程
        self.download_worker = DownloadWorker(
            downloader=self.downloader,
            urls=urls,
            output_dir=output_dir,
            format_id=format_id,
            use_cookies=use_cookies,
            cookies_file=cookies_file,
            prefer_mp4=prefer_mp4
        )
        
        # 连接信号
        self.download_worker.progress_updated.connect(self.update_progress)
        self.download_worker.download_completed.connect(self.download_completed)
        self.download_worker.error_occurred.connect(self.download_error)
        
        # 启动工作线程
        self.download_worker.start()
    
    def cancel_download(self):
        """取消下载"""
        if not self.is_downloading:
            return
        
        # 确认取消
        reply = QMessageBox.question(
            self,
            "确认取消",
            "确定要取消当前下载吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 更新状态栏
            self.update_status_message("正在取消下载...")
            
            # 取消下载
            self.downloader.cancel_download()
            
            # 更新 UI
            self.is_downloading = False
            self.download_button.setEnabled(bool(self.download_dir_input.text()))
            self.cancel_button.setEnabled(False)
            self.progress_bar.setValue(0)
            self.speed_label.setText("速度: 0 KiB/s")
            self.eta_label.setText("剩余时间: 00:00")
            self.video_count_label.setText("0/0")
            
            # 更新状态栏
            self.update_status_message("下载已取消")
    
    def update_progress(self, progress, speed, eta, title, current_index, total_videos):
        """更新进度"""
        self.progress_bar.setValue(int(progress))
        self.speed_label.setText(f"速度: {speed}")
        self.eta_label.setText(f"剩余时间: {eta}")
        self.video_count_label.setText(f"{current_index}/{total_videos}")
        
        # 更新状态栏
        self.update_status_message(f"正在下载: {title} - {progress:.1f}% - {speed}")
    
    def download_completed(self, success, output_dir):
        """下载完成"""
        # 更新 UI
        self.is_downloading = False
        self.download_button.setEnabled(bool(self.download_dir_input.text()))
        self.cancel_button.setEnabled(False)
        
        if success:
            # 显示完成消息
            QMessageBox.information(self, "下载完成", f"视频已成功下载到:\n{output_dir}")
            
            # 显示通知
            self.notification_manager.show_download_complete_notification(
                title=self.title_label.text(),
                output_dir=output_dir
            )
            
            # 更新状态栏
            self.update_status_message("下载完成")
        else:
            # 显示错误消息
            QMessageBox.warning(self, "下载失败", f"下载过程中发生错误:\n{output_dir}")
            
            # 更新状态栏
            self.update_status_message(f"下载失败: {output_dir}")
    
    def download_error(self, error_message):
        """下载错误"""
        QMessageBox.critical(self, "错误", f"下载过程中发生错误:\n{error_message}")
        
        # 更新 UI
        self.is_downloading = False
        self.download_button.setEnabled(bool(self.download_dir_input.text()))
        self.cancel_button.setEnabled(False)
        
        # 更新状态栏
        self.update_status_message(f"下载错误: {error_message}")
