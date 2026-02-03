"""
YouTube Downloader 系统托盘模块
提供系统托盘图标和菜单功能
"""
import os
from typing import Optional, Callable

from PyQt5.QtWidgets import (
    QSystemTrayIcon, QMenu, QAction, QApplication, QMainWindow
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QObject, pyqtSignal

from src.utils.platform import get_project_root
from src.utils.logger import LoggerManager
from src.core.event_bus import event_bus, Events


class SystemTrayManager(QObject):
    """
    系统托盘管理器
    
    特性：
    - 最小化到托盘
    - 下载完成通知
    - 快捷操作菜单
    """
    
    # 信号定义
    show_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    
    def __init__(self, main_window: QMainWindow = None, parent: QObject = None):
        """
        初始化系统托盘管理器
        
        Args:
            main_window: 主窗口引用
            parent: 父对象
        """
        super().__init__(parent)
        
        self.logger = LoggerManager().get_logger()
        self.main_window = main_window
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._menu: Optional[QMenu] = None
        
        # 初始化托盘
        self._init_tray()
        
        # 订阅事件
        self._subscribe_events()
        
        self.logger.info("系统托盘管理器初始化完成")
    
    def _init_tray(self):
        """初始化系统托盘"""
        # 检查系统是否支持托盘
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.logger.warning("系统不支持托盘图标")
            return
        
        # 创建托盘图标
        self._tray_icon = QSystemTrayIcon(self)
        
        # 设置图标
        icon_path = get_project_root() / 'resources' / 'icons' / 'app_icon.ico'
        if icon_path.exists():
            self._tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            # 使用默认图标
            self._tray_icon.setIcon(QApplication.style().standardIcon(
                QApplication.style().SP_MediaPlay
            ))
        
        # 设置提示文字
        self._tray_icon.setToolTip("YouTube Downloader")
        
        # 创建菜单
        self._create_menu()
        
        # 连接信号
        self._tray_icon.activated.connect(self._on_tray_activated)
        
        # 显示托盘图标
        self._tray_icon.show()
    
    def _create_menu(self):
        """创建托盘菜单"""
        self._menu = QMenu()
        
        # 显示主窗口
        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self._show_window)
        self._menu.addAction(show_action)
        
        self._menu.addSeparator()
        
        # 暂停所有下载
        self._pause_action = QAction("暂停所有下载", self)
        self._pause_action.triggered.connect(self._toggle_pause)
        self._pause_action.setEnabled(False)
        self._menu.addAction(self._pause_action)
        
        # 取消所有下载
        cancel_action = QAction("取消所有下载", self)
        cancel_action.triggered.connect(self._cancel_all)
        self._menu.addAction(cancel_action)
        
        self._menu.addSeparator()
        
        # 打开下载目录
        open_dir_action = QAction("打开下载目录", self)
        open_dir_action.triggered.connect(self._open_download_dir)
        self._menu.addAction(open_dir_action)
        
        self._menu.addSeparator()
        
        # 退出
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit)
        self._menu.addAction(quit_action)
        
        # 设置菜单
        if self._tray_icon:
            self._tray_icon.setContextMenu(self._menu)
    
    def _subscribe_events(self):
        """订阅事件"""
        event_bus.subscribe(Events.DOWNLOAD_STARTED, self._on_download_started)
        event_bus.subscribe(Events.DOWNLOAD_COMPLETED, self._on_download_completed)
        event_bus.subscribe(Events.DOWNLOAD_FAILED, self._on_download_failed)
    
    def _on_tray_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_window()
        elif reason == QSystemTrayIcon.Trigger:
            # 单击显示菜单（某些系统）
            pass
    
    def _show_window(self):
        """显示主窗口"""
        if self.main_window:
            self.main_window.showNormal()
            self.main_window.activateWindow()
            self.main_window.raise_()
        self.show_window_requested.emit()
    
    def _toggle_pause(self):
        """切换暂停状态"""
        from src.core.download_queue import download_queue
        
        if download_queue.is_paused():
            download_queue.resume()
            self._pause_action.setText("暂停所有下载")
        else:
            download_queue.pause()
            self._pause_action.setText("恢复所有下载")
    
    def _cancel_all(self):
        """取消所有下载"""
        from src.core.download_queue import download_queue
        download_queue.clear_all()
        self.show_notification("已取消", "已取消所有下载任务")
    
    def _open_download_dir(self):
        """打开下载目录"""
        from src.utils.config import ConfigManager
        import subprocess
        
        config = ConfigManager()
        download_dir = config.get('download_dir', '')
        
        if download_dir and os.path.exists(download_dir):
            # Windows
            if os.name == 'nt':
                subprocess.run(['explorer', download_dir])
            # macOS
            elif os.uname().sysname == 'Darwin':
                subprocess.run(['open', download_dir])
            # Linux
            else:
                subprocess.run(['xdg-open', download_dir])
        else:
            self.show_notification("提示", "下载目录未设置或不存在")
    
    def _quit(self):
        """退出应用"""
        self.quit_requested.emit()
        if self.main_window:
            self.main_window.close()
        QApplication.quit()
    
    def _on_download_started(self, event):
        """处理下载开始事件"""
        self._pause_action.setEnabled(True)
        
        title = event.data.get('title', '视频')
        self.set_tooltip(f"正在下载: {title[:30]}...")
    
    def _on_download_completed(self, event):
        """处理下载完成事件"""
        title = event.data.get('title', '视频')
        self.show_notification(
            "下载完成",
            f"{title[:50]} 已下载完成"
        )
        self.set_tooltip("YouTube Downloader")
    
    def _on_download_failed(self, event):
        """处理下载失败事件"""
        title = event.data.get('title', '视频')
        error = event.data.get('error', '未知错误')
        
        self.show_notification(
            "下载失败",
            f"{title[:30]}: {error[:50]}",
            icon=QSystemTrayIcon.Warning
        )
        self.set_tooltip("YouTube Downloader")
    
    def show_notification(
        self, 
        title: str, 
        message: str, 
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.Information,
        duration: int = 3000
    ):
        """
        显示通知
        
        Args:
            title: 标题
            message: 消息
            icon: 图标类型
            duration: 显示时长（毫秒）
        """
        if self._tray_icon and self._tray_icon.isVisible():
            self._tray_icon.showMessage(title, message, icon, duration)
    
    def set_tooltip(self, text: str):
        """设置提示文字"""
        if self._tray_icon:
            self._tray_icon.setToolTip(text)
    
    def set_icon(self, icon_path: str):
        """设置图标"""
        if self._tray_icon and os.path.exists(icon_path):
            self._tray_icon.setIcon(QIcon(icon_path))
    
    def set_visible(self, visible: bool):
        """设置托盘可见性"""
        if self._tray_icon:
            if visible:
                self._tray_icon.show()
            else:
                self._tray_icon.hide()
    
    def is_visible(self) -> bool:
        """托盘是否可见"""
        return self._tray_icon.isVisible() if self._tray_icon else False
    
    def update_progress(self, progress: float, title: str = ""):
        """
        更新进度（在提示文字中显示）
        
        Args:
            progress: 进度 (0-100)
            title: 标题
        """
        if title:
            self.set_tooltip(f"下载中 ({progress:.0f}%): {title[:30]}...")
        else:
            self.set_tooltip(f"下载中 ({progress:.0f}%)")
    
    def set_downloading_icon(self):
        """设置下载中图标（如果有动态图标的话）"""
        # 可以在这里切换到动态图标
        pass
    
    def set_idle_icon(self):
        """设置空闲图标"""
        icon_path = get_project_root() / 'resources' / 'icons' / 'app_icon.ico'
        if icon_path.exists():
            self.set_icon(str(icon_path))
    
    def cleanup(self):
        """清理资源"""
        if self._tray_icon:
            self._tray_icon.hide()
            self._tray_icon = None
        
        if self._menu:
            self._menu.deleteLater()
            self._menu = None


def create_system_tray(main_window: QMainWindow = None) -> Optional[SystemTrayManager]:
    """
    创建系统托盘（便捷函数）
    
    Args:
        main_window: 主窗口引用
        
    Returns:
        系统托盘管理器或 None（如果不支持）
    """
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None
    
    return SystemTrayManager(main_window)

