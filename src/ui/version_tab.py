"""
YouTube 视频下载工具的版本标签页模块
负责创建和管理版本标签页界面
"""
import os
import sys
import threading
from typing import Optional, List, Dict, Tuple

# 导入 PyQt5 模块
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QGroupBox, QMessageBox, QApplication, QStatusBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QIcon, QFont

# 导入自定义模块
from src.core.version_manager import VersionManager
from src.utils.logger import LoggerManager


class UpdateWorker(QThread):
    """更新工作线程类"""
    
    # 定义信号
    progress_updated = pyqtSignal(int, str)
    update_completed = pyqtSignal(bool, str)
    
    def __init__(self, version_manager: VersionManager, update_type: str, download_url: str):
        """
        初始化更新工作线程
        
        Args:
            version_manager: 版本管理器
            update_type: 更新类型，'yt-dlp' 或 'ffmpeg' 或 'init'
            download_url: 下载URL
        """
        super().__init__()
        self.version_manager = version_manager
        self.update_type = update_type
        self.download_url = download_url
    
    def run(self):
        """执行更新任务"""
        try:
            if self.update_type == 'init':
                success, error = self.version_manager.check_and_download_binaries(
                    self._progress_callback
                )
                self.update_completed.emit(success, "" if success else error)
            elif self.update_type == 'yt-dlp':
                success, version = self.version_manager.update_yt_dlp(
                    self.download_url,
                    self._progress_callback
                )
                self.update_completed.emit(success, version if success else "更新失败")
            else:  # ffmpeg
                success, version = self.version_manager.update_ffmpeg(
                    self.download_url,
                    self._progress_callback
                )
                self.update_completed.emit(success, version if success else "更新失败")
        except Exception as e:
            self.update_completed.emit(False, str(e))
    
    def _progress_callback(self, progress: int, status: str):
        """进度回调函数"""
        self.progress_updated.emit(progress, status)


class VersionCheckThread(QThread):
    """版本检查线程类"""
    
    # 定义信号
    check_completed = pyqtSignal(bool, str, bool, str, str, bool, str, bool, str, str)
    check_error = pyqtSignal(str)
    progress_updated = pyqtSignal(str)
    
    def __init__(self, version_manager: VersionManager):
        """
        初始化版本检查线程
        
        Args:
            version_manager: 版本管理器
        """
        super().__init__()
        self.version_manager = version_manager
    
    def run(self):
        """执行版本检查任务"""
        try:
            # 发送进度信号
            self.progress_updated.emit("正在检查 yt-dlp 版本...")
            
            # 检查 yt-dlp 版本
            yt_dlp_success, yt_dlp_current_version = self.version_manager.get_yt_dlp_version()
            yt_dlp_has_update, yt_dlp_latest_version, yt_dlp_download_url = self.version_manager.check_yt_dlp_update()
            
            # 发送进度信号
            self.progress_updated.emit("正在检查 ffmpeg 版本...")
            
            # 检查 ffmpeg 版本
            ffmpeg_success, ffmpeg_current_version = self.version_manager.get_ffmpeg_version()
            ffmpeg_has_update, ffmpeg_latest_version, ffmpeg_download_url = self.version_manager.check_ffmpeg_update()
            
            # 修正 ffmpeg 最新版本显示问题
            if ffmpeg_latest_version == "last":
                ffmpeg_latest_version = "最新版本"
            
            # 发送信号
            self.check_completed.emit(
                yt_dlp_success, yt_dlp_current_version, yt_dlp_has_update, yt_dlp_latest_version, yt_dlp_download_url,
                ffmpeg_success, ffmpeg_current_version, ffmpeg_has_update, ffmpeg_latest_version, ffmpeg_download_url
            )
        except Exception as e:
            self.check_error.emit(str(e))


class VersionTab(QWidget):
    """版本标签页类"""
    
    def __init__(self, status_bar: QStatusBar = None, auto_check: bool = True):
        """
        初始化版本标签页
        
        Args:
            status_bar: 状态栏
            auto_check: 是否自动检查版本
        """
        super().__init__()
        
        # 初始化日志
        self.logger = LoggerManager().get_logger()
        self.status_bar = status_bar
        
        # 初始化版本管理器
        self.version_manager = VersionManager()
        
        # 更新状态
        self.is_updating_yt_dlp = False
        self.is_updating_ffmpeg = False
        self.yt_dlp_update_worker = None
        self.ffmpeg_update_worker = None
        self.version_check_thread = None
        
        # 版本信息
        self.yt_dlp_current_version = ""
        self.yt_dlp_latest_version = ""
        self.yt_dlp_download_url = ""
        self.ffmpeg_current_version = ""
        self.ffmpeg_latest_version = ""
        self.ffmpeg_download_url = ""
        
        # 初始化 UI
        self.init_ui()
        
        # 记录日志
        self.logger.info("版本标签页初始化完成")
        
        # 检查二进制文件是否存在
        if not self.version_manager.binaries_exist():
            self.logger.info("检测到缺少必要的二进制文件，开始初始化下载")
            self.init_binaries()
        elif auto_check:
            self.check_versions()
        
        # 获取当前脚本所在目录
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_path = os.path.join(base_dir, 'resources', 'icons', 'app_icon.ico')

        # 设置窗口图标
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
    
    def init_ui(self):
        """初始化 UI"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)  # 增加边距
        main_layout.setSpacing(15)  # 增加组件间距
        
        # 创建 yt-dlp 版本信息区域
        yt_dlp_group = QGroupBox("yt-dlp 版本信息")
        yt_dlp_layout = QVBoxLayout(yt_dlp_group)
        yt_dlp_layout.setContentsMargins(15, 15, 15, 15)  # 增加组内边距
        yt_dlp_layout.setSpacing(10)  # 增加组内间距
        
        # 当前版本
        current_version_layout = QHBoxLayout()
        current_version_layout.addWidget(QLabel("当前版本:"))
        self.yt_dlp_current_version_label = QLabel("未检查")
        current_version_layout.addWidget(self.yt_dlp_current_version_label)
        current_version_layout.addStretch()
        yt_dlp_layout.addLayout(current_version_layout)
        
        # 最新版本
        latest_version_layout = QHBoxLayout()
        latest_version_layout.addWidget(QLabel("最新版本:"))
        self.yt_dlp_latest_version_label = QLabel("未检查")
        latest_version_layout.addWidget(self.yt_dlp_latest_version_label)
        latest_version_layout.addStretch()
        yt_dlp_layout.addLayout(latest_version_layout)
        
        # 更新按钮和进度条
        update_layout = QHBoxLayout()
        self.yt_dlp_update_button = QPushButton("更新")
        self.yt_dlp_update_button.clicked.connect(self.update_yt_dlp)
        self.yt_dlp_update_button.setEnabled(False)
        update_layout.addWidget(self.yt_dlp_update_button)
        
        self.yt_dlp_progress_bar = QProgressBar()
        self.yt_dlp_progress_bar.setRange(0, 100)
        self.yt_dlp_progress_bar.setValue(0)
        update_layout.addWidget(self.yt_dlp_progress_bar)
        
        yt_dlp_layout.addLayout(update_layout)
        
        # 状态标签
        self.yt_dlp_status_label = QLabel("")
        yt_dlp_layout.addWidget(self.yt_dlp_status_label)
        
        # 添加 yt-dlp 版本信息区域到主布局
        main_layout.addWidget(yt_dlp_group)
        
        # 创建 ffmpeg 版本信息区域
        ffmpeg_group = QGroupBox("ffmpeg 版本信息")
        ffmpeg_layout = QVBoxLayout(ffmpeg_group)
        ffmpeg_layout.setContentsMargins(15, 15, 15, 15)  # 增加组内边距
        ffmpeg_layout.setSpacing(10)  # 增加组内间距
        
        # 当前版本
        current_version_layout = QHBoxLayout()
        current_version_layout.addWidget(QLabel("当前版本:"))
        self.ffmpeg_current_version_label = QLabel("未检查")
        current_version_layout.addWidget(self.ffmpeg_current_version_label)
        current_version_layout.addStretch()
        ffmpeg_layout.addLayout(current_version_layout)
        
        # 最新版本
        latest_version_layout = QHBoxLayout()
        latest_version_layout.addWidget(QLabel("最新版本:"))
        self.ffmpeg_latest_version_label = QLabel("未检查")
        latest_version_layout.addWidget(self.ffmpeg_latest_version_label)
        latest_version_layout.addStretch()
        ffmpeg_layout.addLayout(latest_version_layout)
        
        # 更新按钮和进度条
        update_layout = QHBoxLayout()
        self.ffmpeg_update_button = QPushButton("更新")
        self.ffmpeg_update_button.clicked.connect(self.update_ffmpeg)
        self.ffmpeg_update_button.setEnabled(False)
        update_layout.addWidget(self.ffmpeg_update_button)
        
        self.ffmpeg_progress_bar = QProgressBar()
        self.ffmpeg_progress_bar.setRange(0, 100)
        self.ffmpeg_progress_bar.setValue(0)
        update_layout.addWidget(self.ffmpeg_progress_bar)
        
        ffmpeg_layout.addLayout(update_layout)
        
        # 状态标签
        self.ffmpeg_status_label = QLabel("")
        ffmpeg_layout.addWidget(self.ffmpeg_status_label)
        
        # 添加 ffmpeg 版本信息区域到主布局
        main_layout.addWidget(ffmpeg_group)
        
        # 添加检查更新按钮
        check_layout = QHBoxLayout()
        check_layout.addStretch()
        
        self.check_updates_button = QPushButton("检查更新")
        self.check_updates_button.clicked.connect(self.check_versions)
        check_layout.addWidget(self.check_updates_button)
        
        main_layout.addLayout(check_layout)
        
        # 添加弹性空间
        main_layout.addStretch()
    
    def update_status_message(self, message):
        """更新状态栏消息"""
        if self.status_bar:
            # 使用 QTimer.singleShot 确保在主线程中更新 UI
            QTimer.singleShot(0, lambda: self.status_bar.showMessage(message, 5000))  # 显示5秒
    
    def check_versions(self):
        """检查版本"""
        # 如果已经在检查中，直接返回
        if hasattr(self, 'version_check_thread') and self.version_check_thread and self.version_check_thread.isRunning():
            return
            
        # 禁用检查更新按钮
        self.check_updates_button.setEnabled(False)
        
        # 更新状态
        self.yt_dlp_status_label.setText("正在检查 yt-dlp 版本...")
        self.ffmpeg_status_label.setText("正在检查 ffmpeg 版本...")
        
        # 更新状态栏
        self.update_status_message("正在检查版本信息...")
        
        # 创建并启动版本检查线程
        self.version_check_thread = VersionCheckThread(self.version_manager)
        self.version_check_thread.check_completed.connect(self.on_version_check_completed)
        self.version_check_thread.check_error.connect(self.on_version_check_error)
        self.version_check_thread.progress_updated.connect(self.update_status_message)
        self.version_check_thread.start()
    
    def on_version_check_completed(self, yt_dlp_success, yt_dlp_current_version, yt_dlp_has_update, 
                                  yt_dlp_latest_version, yt_dlp_download_url, ffmpeg_success, 
                                  ffmpeg_current_version, ffmpeg_has_update, ffmpeg_latest_version, 
                                  ffmpeg_download_url):
        """版本检查完成回调"""
        # 更新 yt-dlp 版本信息
        if yt_dlp_success:
            self.yt_dlp_current_version = yt_dlp_current_version
            self.yt_dlp_current_version_label.setText(yt_dlp_current_version)
        else:
            self.yt_dlp_current_version_label.setText("未安装或无法获取")
        
        if yt_dlp_latest_version:
            self.yt_dlp_latest_version = yt_dlp_latest_version
            self.yt_dlp_latest_version_label.setText(yt_dlp_latest_version)
        else:
            self.yt_dlp_latest_version_label.setText("无法获取")
        
        # 保存下载链接
        self.yt_dlp_download_url = yt_dlp_download_url
        
        # 判断yt-dlp按钮状态
        if not yt_dlp_success:
            self.yt_dlp_update_button.setText("下载")
            self.yt_dlp_update_button.setEnabled(True)
            self.yt_dlp_status_label.setText("未安装，需下载")
        elif yt_dlp_has_update and yt_dlp_download_url:
            self.yt_dlp_update_button.setText("更新")
            self.yt_dlp_update_button.setEnabled(True)
            self.yt_dlp_status_label.setText("有新版本可用")
        else:
            self.yt_dlp_update_button.setText("更新")
            self.yt_dlp_update_button.setEnabled(False)
            self.yt_dlp_status_label.setText("已是最新版本")
        
        # 更新 ffmpeg 版本信息
        if ffmpeg_success:
            self.ffmpeg_current_version = ffmpeg_current_version
            self.ffmpeg_current_version_label.setText(ffmpeg_current_version)
        else:
            self.ffmpeg_current_version_label.setText("未安装或无法获取")
        
        if ffmpeg_latest_version:
            self.ffmpeg_latest_version = ffmpeg_latest_version
            self.ffmpeg_latest_version_label.setText(ffmpeg_latest_version)
        else:
            self.ffmpeg_latest_version_label.setText("无法获取")
        
        # 保存下载链接
        self.ffmpeg_download_url = ffmpeg_download_url
        
        # 判断ffmpeg按钮状态
        if not ffmpeg_success:
            self.ffmpeg_update_button.setText("下载")
            self.ffmpeg_update_button.setEnabled(True)
            self.ffmpeg_status_label.setText("未安装，需下载")
        elif ffmpeg_has_update and ffmpeg_download_url:
            self.ffmpeg_update_button.setText("更新")
            self.ffmpeg_update_button.setEnabled(True)
            self.ffmpeg_status_label.setText("有新版本可用")
        else:
            self.ffmpeg_update_button.setText("更新")
            self.ffmpeg_update_button.setEnabled(False)
            self.ffmpeg_status_label.setText("已是最新版本")
        
        # 启用检查更新按钮
        self.check_updates_button.setEnabled(True)
        
        # 更新状态栏
        self.update_status_message("版本检查完成")
    
    def on_version_check_error(self, error_message):
        """版本检查错误回调"""
        QMessageBox.critical(self, "错误", f"检查版本时发生错误: {error_message}")
        self.yt_dlp_status_label.setText("检查失败")
        self.ffmpeg_status_label.setText("检查失败")
        self.check_updates_button.setEnabled(True)
        
        # 更新状态栏
        self.update_status_message(f"版本检查失败: {error_message}")
        
        # 记录日志
        self.logger.error(f"检查版本时发生错误: {error_message}")
    
    def update_yt_dlp(self):
        """更新 yt-dlp"""
        # 检查是否已在更新
        if self.is_updating_yt_dlp:
            return
        
        # 检查下载 URL
        if not self.yt_dlp_download_url:
            QMessageBox.warning(self, "错误", "无法获取 yt-dlp 下载链接")
            return
        
        # 确认更新
        reply = QMessageBox.question(
            self,
            "确认更新",
            f"确定要将 yt-dlp 从 {self.yt_dlp_current_version} 更新到 {self.yt_dlp_latest_version} 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 更新 UI
        self.is_updating_yt_dlp = True
        self.yt_dlp_update_button.setEnabled(False)
        self.yt_dlp_progress_bar.setValue(0)
        self.yt_dlp_status_label.setText("正在更新...")
        
        # 更新状态栏
        self.update_status_message("正在更新 yt-dlp...")
        
        # 创建并启动更新工作线程
        self.yt_dlp_update_worker = UpdateWorker(
            version_manager=self.version_manager,
            update_type='yt-dlp',
            download_url=self.yt_dlp_download_url
        )
        
        # 连接信号
        self.yt_dlp_update_worker.progress_updated.connect(self.update_yt_dlp_progress)
        self.yt_dlp_update_worker.update_completed.connect(self.yt_dlp_update_completed)
        
        # 启动工作线程
        self.yt_dlp_update_worker.start()
    
    def update_yt_dlp_progress(self, progress, status):
        """更新 yt-dlp 进度"""
        self.yt_dlp_progress_bar.setValue(progress)
        self.yt_dlp_status_label.setText(status)
        
        # 更新状态栏
        self.update_status_message(f"更新 yt-dlp: {progress}% - {status}")
    
    def yt_dlp_update_completed(self, success, result):
        """yt-dlp 更新完成"""
        # 更新 UI
        self.is_updating_yt_dlp = False
        
        if success:
            # 更新版本信息
            self.yt_dlp_current_version = result
            self.yt_dlp_current_version_label.setText(result)
            self.yt_dlp_update_button.setEnabled(False)
            self.yt_dlp_status_label.setText("更新成功")
            
            # 显示成功消息
            QMessageBox.information(self, "更新成功", f"yt-dlp 已成功更新到版本 {result}")
            
            # 更新状态栏
            self.update_status_message(f"yt-dlp 更新成功: 版本 {result}")
        else:
            # 启用更新按钮
            self.yt_dlp_update_button.setEnabled(True)
            self.yt_dlp_status_label.setText(f"更新失败: {result}")
            
            # 显示错误消息
            QMessageBox.critical(self, "更新失败", f"yt-dlp 更新失败: {result}")
            
            # 更新状态栏
            self.update_status_message(f"yt-dlp 更新失败: {result}")
    
    def update_ffmpeg(self):
        """更新 ffmpeg"""
        # 检查是否已在更新
        if self.is_updating_ffmpeg:
            return
        
        # 检查下载 URL
        if not self.ffmpeg_download_url:
            QMessageBox.warning(self, "错误", "无法获取 ffmpeg 下载链接")
            return
        
        # 确认更新
        reply = QMessageBox.question(
            self,
            "确认更新",
            f"确定要将 ffmpeg 从 {self.ffmpeg_current_version} 更新到 {self.ffmpeg_latest_version} 吗？\n\n注意：更新可能需要几分钟时间。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 更新 UI
        self.is_updating_ffmpeg = True
        self.ffmpeg_update_button.setEnabled(False)
        self.ffmpeg_progress_bar.setValue(0)
        self.ffmpeg_status_label.setText("正在更新...")
        
        # 更新状态栏
        self.update_status_message("正在更新 ffmpeg...")
        
        # 创建并启动更新工作线程
        self.ffmpeg_update_worker = UpdateWorker(
            version_manager=self.version_manager,
            update_type='ffmpeg',
            download_url=self.ffmpeg_download_url
        )
        
        # 连接信号
        self.ffmpeg_update_worker.progress_updated.connect(self.update_ffmpeg_progress)
        self.ffmpeg_update_worker.update_completed.connect(self.ffmpeg_update_completed)
        
        # 启动工作线程
        self.ffmpeg_update_worker.start()
    
    def update_ffmpeg_progress(self, progress, status):
        """更新 ffmpeg 进度"""
        self.ffmpeg_progress_bar.setValue(progress)
        self.ffmpeg_status_label.setText(status)
        
        # 更新状态栏
        self.update_status_message(f"更新 ffmpeg: {progress}% - {status}")
    
    def ffmpeg_update_completed(self, success, result):
        """ffmpeg 更新完成"""
        # 更新 UI
        self.is_updating_ffmpeg = False
        
        if success:
            # 更新版本信息
            self.ffmpeg_current_version = result
            self.ffmpeg_current_version_label.setText(result)
            self.ffmpeg_update_button.setEnabled(False)
            self.ffmpeg_status_label.setText("更新成功")
            
            # 显示成功消息
            QMessageBox.information(self, "更新成功", f"ffmpeg 已成功更新到版本 {result}")
            
            # 更新状态栏
            self.update_status_message(f"ffmpeg 更新成功: 版本 {result}")
        else:
            # 启用更新按钮
            self.ffmpeg_update_button.setEnabled(True)
            self.ffmpeg_status_label.setText(f"更新失败: {result}")
            
            # 显示错误消息
            QMessageBox.critical(self, "更新失败", f"ffmpeg 更新失败: {result}")
            
            # 更新状态栏
            self.update_status_message(f"ffmpeg 更新失败: {result}")

    def init_binaries(self):
        """初始化下载必要的二进制文件"""
        # 更新状态
        self.yt_dlp_status_label.setText("正在初始化下载...")
        self.ffmpeg_status_label.setText("正在初始化下载...")
        
        # 更新状态栏
        self.update_status_message("正在初始化下载必要的文件...")
        
        # 创建并启动初始化下载线程
        self.init_worker = UpdateWorker(
            version_manager=self.version_manager,
            update_type='init',
            download_url=None
        )
        
        # 连接信号
        self.init_worker.progress_updated.connect(self.update_init_progress)
        self.init_worker.update_completed.connect(self.init_completed)
        
        # 启动工作线程
        self.init_worker.start()
    
    def update_init_progress(self, progress, status):
        """更新初始化进度"""
        self.yt_dlp_progress_bar.setValue(progress)
        self.ffmpeg_progress_bar.setValue(progress)
        self.yt_dlp_status_label.setText(status)
        self.ffmpeg_status_label.setText(status)
        
        # 更新状态栏
        self.update_status_message(f"初始化下载: {progress}% - {status}")
    
    def init_completed(self, success, result):
        """初始化完成"""
        if success:
            # 更新状态
            self.yt_dlp_status_label.setText("初始化完成")
            self.ffmpeg_status_label.setText("初始化完成")
            
            # 更新状态栏
            self.update_status_message("初始化下载完成")
            
            # 检查版本
            self.check_versions()
        else:
            # 更新状态
            self.yt_dlp_status_label.setText(f"初始化失败: {result}")
            self.ffmpeg_status_label.setText(f"初始化失败: {result}")
            
            # 更新状态栏
            self.update_status_message(f"初始化下载失败: {result}")
            
            # 显示错误消息
            QMessageBox.critical(self, "初始化失败", f"无法下载必要的文件: {result}\n请检查网络连接后重试。")
