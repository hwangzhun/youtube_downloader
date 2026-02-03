"""
YouTube Downloader 的主窗口模块
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
    QAction, QMenu, QDialog, QSplashScreen, QProgressDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFont, QPixmap

# 导入自定义模块
from src.ui.download_tab import DownloadTab
from src.ui.multi_download_tab import MultiDownloadTab
from src.ui.channel_download_tab import ChannelDownloadTab
from src.ui.version_tab import VersionTab
from src.core.version_manager import VersionManager
from src.utils.logger import LoggerManager
from src.utils.config import ConfigManager
from src.ui.cookie_tab import CookieTab
from src.ui.proxy_tab import ProxyTab
from src.config.get_software_version import get_software_version

class VersionCheckThread(QThread):
    """版本检查线程类"""
    
    def __init__(self, version_tab):
        """初始化版本检查线程"""
        super().__init__()
        self.version_tab = version_tab
    
    def run(self):
        """执行版本检查"""
        # 延迟一段时间再执行版本检查，避免影响启动速度
        self.msleep(500)  # 延迟500毫秒
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
        icon_path = os.path.join(base_dir, 'resources', 'icons', 'app_icon_horizontal.png')
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # 应用图标
        if os.path.exists(icon_path):
            icon_label = QLabel()
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label.setPixmap(pixmap)
                icon_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(icon_label)
        
        # 应用名称
        app_name_label = QLabel("YouTube DownLoader")
        app_name_label.setAlignment(Qt.AlignCenter)
        app_name_label.setStyleSheet("font-size: 18px; font-weight: normal;")
        layout.addWidget(app_name_label)
        
        # 版本信息
        version_label = QLabel(f"版本 v{get_software_version()}")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # 作者信息
        author_label = QLabel("By Hwangzhun")
        author_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(author_label)
        
        # 版权信息
        copyright_label = QLabel("许可：MIT 许可证")
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)
        
        # GitHub 信息
        github_label = QLabel('<a href="https://github.com/hwangzhun/youtube_downloader">GitHub</a>')
        github_label.setOpenExternalLinks(True)
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
    
    def __init__(self, splash_screen=None, skip_update_check=False):
        """
        初始化主窗口
        
        Args:
            splash_screen: 启动画面
            skip_update_check: 是否跳过更新检查
        """
        super().__init__()
        
        # 保存启动画面引用
        self.splash_screen = splash_screen
        
        # 初始化日志和配置
        self.logger = LoggerManager().get_logger()
        self.config_manager = ConfigManager()
        
        # 初始化版本管理器
        self.version_manager = VersionManager()
        
        # 设置窗口属性
        self.setWindowTitle(f"YouTube DownLoader - v{get_software_version()}")
        self.setMinimumSize(800, 600)
        
        # 获取当前脚本所在目录
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # icon_path = os.path.join(base_dir, 'resources', 'icons', 'app_icon.ico')
        icon_vertical_path = os.path.join(base_dir, 'resources', 'icons', 'app_icon.ico')
        
        # 设置窗口图标
        if os.path.exists(icon_vertical_path):
            self.setWindowIcon(QIcon(icon_vertical_path))
        
        # 初始化 UI
        self.init_ui()
        
        # 初始化更新检查
        if not skip_update_check:
            self.check_updates()
        
        # 关闭启动画面
        if self.splash_screen:
            self.splash_screen.finish(self)
            self.splash_screen = None
        
        # 检查 JavaScript 运行时
        self.check_javascript_runtime()
        
        # 记录日志
        self.logger.info("主窗口初始化完成")
    
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
            self.splash_screen.showMessage("正在加载界面组件...", Qt.AlignBottom | Qt.AlignCenter, Qt.black)
        
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
                padding: 8px 20px;  /* 增加水平内边距 */
                margin-right: 2px;
                font-size: 14px;
                min-width: 100px;  /* 设置最小宽度 */
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
            self.splash_screen.showMessage("正在加载下载模块...", Qt.AlignBottom | Qt.AlignCenter, Qt.black)
        
        # 创建下载标签页
        self.cookie_tab = CookieTab(self.status_bar)
        self.proxy_tab = ProxyTab(self.config_manager, self.status_bar)
        self.download_tab = DownloadTab(self.config_manager, self.status_bar, self.cookie_tab)
        self.multi_download_tab = MultiDownloadTab(self.config_manager, self.status_bar, self.cookie_tab)
        self.channel_download_tab = ChannelDownloadTab(self.config_manager, self.status_bar, self.cookie_tab)
        self.version_tab = VersionTab(self.status_bar, auto_check=False)
        
        # 添加标签页
        self.tab_widget.addTab(self.download_tab, "单视频下载")
        self.tab_widget.addTab(self.multi_download_tab, "多视频下载")
        self.tab_widget.addTab(self.channel_download_tab, "频道下载")
        self.tab_widget.addTab(self.cookie_tab, "Cookie")
        self.tab_widget.addTab(self.proxy_tab, "代理")
        self.tab_widget.addTab(self.version_tab, "版本")
        
        # 添加标签页到主布局
        main_layout.addWidget(self.tab_widget)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 设置状态栏初始状态
        self.status_bar.showMessage("就绪")
        
        # 添加作者信息到状态栏
        self.author_label = QLabel("By Hwangzhun | MIT 许可")
        self.author_label.setStyleSheet("color: #666666; padding: 0 8px;")
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
    
    def check_updates(self):
        """检查更新"""
        try:
            # TODO: 实现更新检查逻辑
            pass
        except Exception as e:
            self.logger.error(f"检查更新失败: {str(e)}")
    
    def check_binaries(self):
        """检查并下载必要的二进制文件"""
        try:
            # 优先判断是否都存在
            if self.version_manager.binaries_exist():
                self.logger.info("二进制文件已存在，无需下载")
                return
            self.logger.info("开始检查二进制文件")
            # 创建进度对话框
            progress = QProgressDialog("正在检查必要的组件...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle("初始化")
            progress.setAutoClose(True)
            progress.setAutoReset(True)
            def update_progress(value, status):
                progress.setValue(value)
                progress.setLabelText(status)
            # 检查并下载二进制文件
            success, error = self.version_manager.check_and_download_binaries(update_progress)
            if not success:
                self.logger.error(f"检查二进制文件失败: {error}")
                QMessageBox.critical(self, "错误", f"检查必要的组件时发生错误：\n{error}")
                sys.exit(1)
            self.logger.info("二进制文件检查完成")
        except Exception as e:
            self.logger.error(f"检查二进制文件时发生错误: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "错误", f"检查必要的组件时发生错误：\n{str(e)}")
            sys.exit(1)
    
    def check_javascript_runtime(self):
        """检查 JavaScript 运行时，如果没有则提示用户"""
        from src.utils.platform import find_javascript_runtime
        import webbrowser
        
        runtime = find_javascript_runtime()
        if not runtime:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("缺少 JavaScript 运行时")
            msg.setText("检测到您的系统未安装 JavaScript 运行时")
            msg.setInformativeText(
                "YouTube 现在需要 JavaScript 运行时来提取视频信息。\n\n"
                "推荐安装 Node.js：https://nodejs.org/\n\n"
                "您可以选择自动安装（需要 Windows 10 1709+ 或 Windows 11）\n"
                "或手动下载安装。安装完成后请重启应用程序。"
            )
            
            # 添加按钮
            auto_install = QPushButton("自动安装 Node.js")
            open_nodejs = QPushButton("打开 Node.js 官网")
            ignore = QPushButton("稍后提醒")
            
            msg.addButton(auto_install, QMessageBox.ActionRole)
            msg.addButton(open_nodejs, QMessageBox.ActionRole)
            msg.addButton(ignore, QMessageBox.RejectRole)
            
            result = msg.exec_()
            
            if result == 0:  # 自动安装 Node.js
                self.logger.info("用户选择自动安装 Node.js")
                self._install_nodejs_via_winget()
            elif result == 1:  # 打开 Node.js 官网
                webbrowser.open('https://nodejs.org/')
                self.logger.info("用户点击打开 Node.js 官网")
            else:
                self.logger.info("用户选择稍后提醒")
        else:
            self.logger.info(f"检测到 JavaScript 运行时: {runtime}")
    
    def _install_nodejs_via_winget(self):
        """使用 winget 安装 Node.js"""
        import subprocess
        import webbrowser
        
        # 显示安装进度对话框
        progress = QProgressDialog("正在安装 Node.js，请稍候...", "取消", 0, 0, self)
        progress.setWindowTitle("安装 Node.js")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()
        
        try:
            # 检查 winget 是否可用
            check_winget = subprocess.run(
                ['winget', '--version'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            if check_winget.returncode != 0:
                progress.close()
                QMessageBox.warning(
                    self, 
                    "winget 不可用",
                    "您的系统未安装 winget（Windows 包管理器）。\n\n"
                    "请手动下载安装 Node.js，或升级到 Windows 10 1709+ / Windows 11。"
                )
                webbrowser.open('https://nodejs.org/')
                return
            
            # 使用 winget 安装 Node.js LTS
            self.logger.info("开始使用 winget 安装 Node.js LTS")
            install_process = subprocess.run(
                [
                    'winget', 'install', 'OpenJS.NodeJS.LTS',
                    '--accept-source-agreements',
                    '--accept-package-agreements',
                    '--silent'
                ],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            progress.close()
            
            if install_process.returncode == 0:
                self.logger.info("Node.js 安装成功")
                QMessageBox.information(
                    self,
                    "安装成功",
                    "Node.js 已成功安装！\n\n"
                    "请重启应用程序以使更改生效。"
                )
            else:
                # 检查是否已安装
                if "已安装" in install_process.stdout or "already installed" in install_process.stdout.lower():
                    self.logger.info("Node.js 已经安装")
                    QMessageBox.information(
                        self,
                        "已安装",
                        "Node.js 已经安装在您的系统中。\n\n"
                        "请重启应用程序以使更改生效。"
                    )
                else:
                    self.logger.error(f"Node.js 安装失败: {install_process.stderr}")
                    QMessageBox.warning(
                        self,
                        "安装失败",
                        f"自动安装失败，请手动下载安装 Node.js。\n\n"
                        f"错误信息：{install_process.stderr[:200] if install_process.stderr else '未知错误'}"
                    )
                    webbrowser.open('https://nodejs.org/')
                    
        except FileNotFoundError:
            progress.close()
            self.logger.error("winget 命令未找到")
            QMessageBox.warning(
                self,
                "winget 不可用",
                "您的系统未安装 winget（Windows 包管理器）。\n\n"
                "请手动下载安装 Node.js。"
            )
            webbrowser.open('https://nodejs.org/')
        except Exception as e:
            progress.close()
            self.logger.error(f"安装 Node.js 时发生错误: {str(e)}")
            QMessageBox.warning(
                self,
                "安装错误",
                f"安装过程中发生错误：{str(e)}\n\n"
                "请手动下载安装 Node.js。"
            )
            webbrowser.open('https://nodejs.org/')
    
    def closeEvent(self, event):
        """关闭窗口事件处理"""
        # 保存配置
        self.config_manager.save_config()
        
        # 记录日志
        self.logger.info("应用程序关闭")
        
        # 接受关闭事件
        event.accept()
