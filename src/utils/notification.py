"""
YouTube Downloader 的通知管理模块
负责处理下载完成通知和其他系统通知
"""
import os
import sys
import tempfile
from typing import Optional
from src.utils.logger import LoggerManager

logger = LoggerManager().get_logger()


class NotificationManager:
    """通知管理类"""
    
    def __init__(self):
        """初始化通知管理器"""
        # 检查操作系统
        self.is_windows = sys.platform.startswith('win')
        
        # Windows 通知相关
        self.win_notification_initialized = False
        self.win_notification_module = None
    
    def _init_windows_notification(self) -> bool:
        """
        初始化 Windows 通知模块
        
        Returns:
            是否成功初始化
        """
        if not self.is_windows:
            return False
        
        if self.win_notification_initialized:
            return True
        
        try:
            # 尝试导入 win10toast 模块
            from win10toast import ToastNotifier
            self.win_notification_module = ToastNotifier()
            self.win_notification_initialized = True
            return True
        except ImportError:
            try:
                # 尝试导入 winotify 模块
                from winotify import Notification
                self.win_notification_module = "winotify"
                self.win_notification_initialized = True
                return True
            except ImportError:
                return False
    
    def show_download_complete_notification(self, title: str, output_dir: str, icon_path: Optional[str] = None) -> bool:
        """
        显示下载完成通知
        
        Args:
            title: 视频标题
            output_dir: 输出目录
            icon_path: 图标路径
            
        Returns:
            是否成功显示通知
        """
        if self.is_windows:
            return self._show_windows_notification(
                title="下载完成",
                message=f"视频 '{title}' 已下载完成\n保存位置: {output_dir}",
                icon_path=icon_path,
                duration=5
            )
        else:
            # 非 Windows 系统暂不支持通知
            return False
    
    def show_error_notification(self, error_message: str, icon_path: Optional[str] = None) -> bool:
        """
        显示错误通知
        
        Args:
            error_message: 错误信息
            icon_path: 图标路径
            
        Returns:
            是否成功显示通知
        """
        if self.is_windows:
            return self._show_windows_notification(
                title="错误",
                message=error_message,
                icon_path=icon_path,
                duration=5
            )
        else:
            # 非 Windows 系统暂不支持通知
            return False
    
    def _show_windows_notification(self, title: str, message: str, icon_path: Optional[str] = None, duration: int = 5) -> bool:
        """
        显示 Windows 通知
        
        Args:
            title: 通知标题
            message: 通知内容
            icon_path: 图标路径
            duration: 显示时长（秒）
            
        Returns:
            是否成功显示通知
        """
        if not self._init_windows_notification():
            return False
        
        try:
            # 使用默认图标
            if icon_path is None or not os.path.exists(icon_path):
                # 获取当前脚本所在目录
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                icon_path = os.path.join(base_dir, 'resources', 'icons', 'app_icon.ico')
                
                # 如果图标不存在，则使用临时文件
                if not os.path.exists(icon_path):
                    icon_path = None
            
            # 根据不同的通知模块显示通知
            if self.win_notification_module == "winotify":
                from winotify import Notification
                
                # 创建通知对象
                notification = Notification(
                    app_id="YouTube 视频下载工具",
                    title=title,
                    msg=message,
                    duration="short"
                )
                
                # 设置图标
                if icon_path:
                    notification.set_icon(icon_path)
                
                # 显示通知
                notification.show()
                return True
            else:
                # 使用 win10toast
                return self.win_notification_module.show_toast(
                    title=title,
                    msg=message,
                    icon_path=icon_path,
                    duration=duration,
                    threaded=True
                )
        except Exception as e:
            logger.error(f"显示通知时发生错误: {str(e)}")
            return False
