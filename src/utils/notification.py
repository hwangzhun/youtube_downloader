"""
YouTube 視頻下載工具的通知管理模塊
負責處理下載完成通知和其他系統通知
"""
import os
import sys
import tempfile
from typing import Optional


class NotificationManager:
    """通知管理類"""
    
    def __init__(self):
        """初始化通知管理器"""
        # 檢查操作系統
        self.is_windows = sys.platform.startswith('win')
        
        # Windows 通知相關
        self.win_notification_initialized = False
        self.win_notification_module = None
    
    def _init_windows_notification(self) -> bool:
        """
        初始化 Windows 通知模塊
        
        Returns:
            是否成功初始化
        """
        if not self.is_windows:
            return False
        
        if self.win_notification_initialized:
            return True
        
        try:
            # 嘗試導入 win10toast 模塊
            from win10toast import ToastNotifier
            self.win_notification_module = ToastNotifier()
            self.win_notification_initialized = True
            return True
        except ImportError:
            try:
                # 嘗試導入 winotify 模塊
                from winotify import Notification
                self.win_notification_module = "winotify"
                self.win_notification_initialized = True
                return True
            except ImportError:
                return False
    
    def show_download_complete_notification(self, title: str, output_dir: str, icon_path: Optional[str] = None) -> bool:
        """
        顯示下載完成通知
        
        Args:
            title: 視頻標題
            output_dir: 輸出目錄
            icon_path: 圖標路徑
            
        Returns:
            是否成功顯示通知
        """
        if self.is_windows:
            return self._show_windows_notification(
                title="下載完成",
                message=f"視頻 '{title}' 已下載完成\n保存位置: {output_dir}",
                icon_path=icon_path,
                duration=5
            )
        else:
            # 非 Windows 系統暫不支持通知
            return False
    
    def show_error_notification(self, error_message: str, icon_path: Optional[str] = None) -> bool:
        """
        顯示錯誤通知
        
        Args:
            error_message: 錯誤信息
            icon_path: 圖標路徑
            
        Returns:
            是否成功顯示通知
        """
        if self.is_windows:
            return self._show_windows_notification(
                title="錯誤",
                message=error_message,
                icon_path=icon_path,
                duration=5
            )
        else:
            # 非 Windows 系統暫不支持通知
            return False
    
    def _show_windows_notification(self, title: str, message: str, icon_path: Optional[str] = None, duration: int = 5) -> bool:
        """
        顯示 Windows 通知
        
        Args:
            title: 通知標題
            message: 通知內容
            icon_path: 圖標路徑
            duration: 顯示時長（秒）
            
        Returns:
            是否成功顯示通知
        """
        if not self._init_windows_notification():
            return False
        
        try:
            # 使用默認圖標
            if icon_path is None or not os.path.exists(icon_path):
                # 獲取當前腳本所在目錄
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                icon_path = os.path.join(base_dir, 'resources', 'icons', 'app_icon.ico')
                
                # 如果圖標不存在，則使用臨時文件
                if not os.path.exists(icon_path):
                    icon_path = None
            
            # 根據不同的通知模塊顯示通知
            if self.win_notification_module == "winotify":
                from winotify import Notification
                
                # 創建通知對象
                notification = Notification(
                    app_id="YouTube 視頻下載工具",
                    title=title,
                    msg=message,
                    duration="short"
                )
                
                # 設置圖標
                if icon_path:
                    notification.set_icon(icon_path)
                
                # 顯示通知
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
            print(f"顯示通知時發生錯誤: {str(e)}")
            return False
