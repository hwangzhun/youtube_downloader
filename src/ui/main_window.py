"""
YouTube 视频下载工具的主窗口模块
负责创建和管理主窗口界面
"""
import os
import sys
import threading
from typing import Optional, List, Dict, Tuple

# 导入 PyQt5 模块
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QTextEdit,
    QProgressBar, QFileDialog, QRadioButton, QComboBox,
    QMessageBox, QGroupBox, QSplitter, QFrame, QStatusBar,
    QAction, QMenu, QDialog, QSplashScreen
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QIcon, QFont, QPixmap

# 导入自定义模块
from src.ui.download_tab import DownloadTab
from src.ui.version_tab import VersionTab
from src.utils.logger import LoggerManager
from src.utils.config import ConfigManager


class VersionCheckThread(QThread):
    """版本检查线程类"""
    
    def __init__(self, version_tab):
        """初始化版本检查线程"""
        super().__init__()
        self.version_tab = version_tab
    
    def run(self):
        """执行版本检查"""
        # 延迟一段时间再执行版本检查，避免影响启动速度
        self.msleep(1000)  # 延迟1秒
        self.version_tab.check_versions()


class AboutDialog(QDialog):
    """关于对话框类"""
    
    def __init__(self, parent=None):
        """初始化关于对话框"""
        super().__init__(parent)
        
        # 设置窗口属性
        self.setWindowTitle("关于")
        self.setFixedSize(400, 350)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # 获取图标路径
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_path = os.path.join(base_dir, 'resources', 'icons', 'app_icon.ico')
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # 应用图标
        if os.path.exists(icon_path):
            icon_label = QLabel()
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label.setPixmap(pixmap)
                icon_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(icon_label)
        
        # 应用名称
        app_name_label = QLabel("YouTube 视频下载工具")
        app_name_label.setAlignment(Qt.AlignCenter)
        app_name_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(app_name_label)
        
        # 版本信息
        version_label = QLabel("版本 1.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # 作者信息
        author_label = QLabel("作者: Hwangzhun")
        author_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(author_label)
        
        # 版权信息
        copyright_label = QLabel("版权所有 © 2025 - MIT 许可证")
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)
        
        # GitHub 信息
        github_label = QLabel("GitHub: ")
        github_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(github_label)
        
        # 描述信息
        description_label = QLabel("这是一个简单易用的 YouTube 视频下载工具，支持单条或多条视频下载，可选择清晰度和格式，并提供下载进度显示。")
        description_label.setWordWrap(True)
        description_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(description_label)
        
        # 弹性空间
        layout.addStretch()
        
        # 确定按钮
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        ok_button.setFixedWidth(100)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self, splash_screen=None):
        """
        初始化主窗口
        
        Args:
            splash_screen: 启动画面
        """
        super().__init__()
        
        # 保存启动画面引用
        self.splash_screen = splash_screen
        
        # 初始化日志和配置
        self.logger = LoggerManager().get_logger()
        self.config_manager = ConfigManager()
        
        # 设置窗口属性
        self.setWindowTitle("YouTube 视频下载工具 - Hwangzhun")
        self.setMinimumSize(800, 600)
        
        # 获取当前脚本所在目录
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_path = os.path.join(base_dir, 'resources', 'icons', 'app_icon.ico')
        
        # 设置窗口图标
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 更新启动画面状态
        if self.splash_screen:
            self.splash_screen.showMessage("正在初始化界面...", Qt.AlignBottom | Qt.AlignCenter, Qt.white)
        
        # 初始化 UI
        self.init_ui()
        
        # 记录日志
        self.logger.info("主窗口初始化完成")
        
        # 延迟执行版本检查
        QTimer.singleShot(500, self.delayed_initialization)
    
    def delayed_initialization(self):
        """延迟初始化，在主界面显示后执行"""
        # 关闭启动画面
        if self.splash_screen:
            self.splash_screen.finish(self)
        
        # 在后台线程中执行版本检查
        self.version_check_thread = VersionCheckThread(self.version_tab)
        self.version_check_thread.start()
    
    def init_ui(self):
        """初始化 UI"""
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 更新启动画面状态
        if self.splash_screen:
            self.splash_screen.showMessage("正在加载界面组件...", Qt.AlignBottom | Qt.AlignCenter, Qt.white)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #C0C0C0;
                border-radius: 3px;
                background-color: #F2F2F2;
            }
            QTabBar::tab {
                background-color: #E0E0E0;
                border: 1px solid #C0C0C0;
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                padding: 8px 12px;
                margin-right: 2px;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background-color: #0078D7;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #D0D0D0;
            }
        """)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 更新启动画面状态
        if self.splash_screen:
            self.splash_screen.showMessage("正在加载下载模块...", Qt.AlignBottom | Qt.AlignCenter, Qt.white)
        
        # 创建下载标签页
        self.download_tab = DownloadTab(self.config_manager, self.status_bar)
        self.tab_widget.addTab(self.download_tab, "下载")
        
        # 更新启动画面状态
        if self.splash_screen:
            self.splash_screen.showMessage("正在加载版本信息模块...", Qt.AlignBottom | Qt.AlignCenter, Qt.white)
        
        # 创建版本标签页 - 不立即检查版本
        self.version_tab = VersionTab(self.status_bar, auto_check=False)
        self.tab_widget.addTab(self.version_tab, "版本信息")
        
        # 添加标签页到主布局
        main_layout.addWidget(self.tab_widget)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 设置状态栏
        self.status_bar.showMessage("就绪")
        
        # 添加作者信息到状态栏
        self.author_label = QLabel("作者: Hwangzhun | MIT 许可证")
        self.status_bar.addPermanentWidget(self.author_label)
        
        # 应用 Metro 风格
        self.apply_metro_style()
    
    def create_menu_bar(self):
        """创建菜单栏"""
        # 创建菜单栏
        menu_bar = self.menuBar()
        
        # 文件菜单
        file_menu = menu_bar.addMenu("文件")
        
        # 退出动作
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        
        # 关于动作
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def show_about_dialog(self):
        """显示关于对话框"""
        about_dialog = AboutDialog(self)
        about_dialog.exec_()
    
    def apply_metro_style(self):
        """应用 Metro 风格"""
        # 设置全局样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F2F2F2;
            }
            QWidget {
                font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1C86E0;
            }
            QPushButton:pressed {
                background-color: #005A9E;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #888888;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #C0C0C0;
                border-radius: 3px;
                padding: 6px;
                background-color: white;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 1px solid #0078D7;
            }
            QProgressBar {
                border: 1px solid #C0C0C0;
                border-radius: 3px;
                background-color: white;
                text-align: center;
                color: black;
            }
            QProgressBar::chunk {
                background-color: #0078D7;
            }
            QLabel {
                color: #333333;
            }
            QGroupBox {
                border: 1px solid #C0C0C0;
                border-radius: 3px;
                margin-top: 12px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
            }
            QRadioButton {
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QStatusBar {
                background-color: #E0E0E0;
                color: #333333;
            }
            QMenuBar {
                background-color: #F2F2F2;
                border-bottom: 1px solid #C0C0C0;
            }
            QMenuBar::item {
                padding: 6px 10px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background-color: #0078D7;
                color: white;
            }
            QMenu {
                background-color: white;
                border: 1px solid #C0C0C0;
            }
            QMenu::item {
                padding: 6px 20px 6px 20px;
            }
            QMenu::item:selected {
                background-color: #0078D7;
                color: white;
            }
        """)
    
    def closeEvent(self, event):
        """关闭窗口事件处理"""
        # 保存配置
        self.config_manager.save_config()
        
        # 记录日志
        self.logger.info("应用程序关闭")
        
        # 接受关闭事件
        event.accept()
