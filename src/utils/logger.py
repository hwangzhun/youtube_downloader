"""
YouTube 視頻下載工具的日誌管理模塊
負責處理日誌記錄功能
"""
import os
import sys
import logging
import platform
import traceback
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Dict


class LoggerManager:
    """日誌管理類"""
    
    def __init__(self, log_file: str = None, log_level: int = logging.INFO):
        """
        初始化日誌管理器
        
        Args:
            log_file: 日誌文件路徑，如果為 None 則使用默認路徑
            log_level: 日誌級別
        """
        # 獲取應用程序數據目錄
        if sys.platform.startswith('win'):
            app_data_dir = os.path.join(os.environ.get('APPDATA', ''), 'YouTubeDownloader', 'logs')
        else:
            app_data_dir = os.path.join(os.path.expanduser('~'), '.youtube_downloader', 'logs')
        
        # 確保目錄存在
        os.makedirs(app_data_dir, exist_ok=True)
        
        # 設置日誌文件路徑
        self.log_file = log_file or os.path.join(
            app_data_dir, 
            f"youtube_downloader_{datetime.now().strftime('%Y%m%d')}.log"
        )
        
        # 創建日誌記錄器
        self.logger = logging.getLogger('youtube_downloader')
        self.logger.setLevel(log_level)
        
        # 清除現有處理器
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # 添加文件處理器
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        
        # 添加控制台處理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # 設置詳細的日誌格式
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        file_handler.setFormatter(detailed_formatter)
        console_handler.setFormatter(detailed_formatter)
        
        # 添加處理器到記錄器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # 記錄系統信息
        self._log_system_info()
    
    def _log_system_info(self):
        """記錄系統信息"""
        system_info = self._get_system_info()
        self.info(f"系統信息: {system_info}")
    
    def _get_system_info(self) -> Dict[str, str]:
        """获取系统信息"""
        try:
            import platform
            import psutil
            
            info = {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'processor': platform.processor(),
            }
            
            # 获取内存信息
            try:
                memory = psutil.virtual_memory()
                info['memory'] = f"总内存: {self._format_size(memory.total)}, 可用: {self._format_size(memory.available)}"
            except:
                info['memory'] = "无法获取内存信息"
            
            # 获取磁盘空间信息
            try:
                disk = psutil.disk_usage('/')
                info['disk_space'] = f"总空间: {self._format_size(disk.total)}, 可用: {self._format_size(disk.free)}"
            except:
                info['disk_space'] = "无法获取磁盘空间信息"
            
            return info
        except Exception as e:
            self.logger.error(f"获取系统信息时发生错误: {str(e)}", exc_info=True)
            return {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'processor': platform.processor(),
                'memory': "无法获取内存信息",
                'disk_space': "无法获取磁盘空间信息"
            }
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"
    
    def get_logger(self) -> logging.Logger:
        """
        獲取日誌記錄器
        
        Returns:
            日誌記錄器
        """
        return self.logger
    
    def debug(self, message: str) -> None:
        """
        記錄調試信息
        
        Args:
            message: 日誌信息
        """
        self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """
        記錄一般信息
        
        Args:
            message: 日誌信息
        """
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """
        記錄警告信息
        
        Args:
            message: 日誌信息
        """
        self.logger.warning(message)
    
    def error(self, message: str, exc_info: bool = True) -> None:
        """
        記錄錯誤信息
        
        Args:
            message: 日誌信息
            exc_info: 是否包含異常信息
        """
        if exc_info:
            self.logger.error(f"{message}\n{traceback.format_exc()}")
        else:
            self.logger.error(message)
    
    def critical(self, message: str, exc_info: bool = True) -> None:
        """
        記錄嚴重錯誤信息
        
        Args:
            message: 日誌信息
            exc_info: 是否包含異常信息
        """
        if exc_info:
            self.logger.critical(f"{message}\n{traceback.format_exc()}")
        else:
            self.logger.critical(message)
    
    def log_download_progress(self, url: str, progress: float, status: str) -> None:
        """
        記錄下載進度
        
        Args:
            url: 視頻URL
            progress: 下載進度（0-100）
            status: 下載狀態
        """
        self.info(f"下載進度 - URL: {url}, 進度: {progress:.2f}%, 狀態: {status}")
    
    def log_download_complete(self, url: str, output_path: str, duration: float) -> None:
        """
        記錄下載完成信息
        
        Args:
            url: 視頻URL
            output_path: 輸出文件路徑
            duration: 下載耗時（秒）
        """
        self.info(f"下載完成 - URL: {url}, 保存路徑: {output_path}, 耗時: {duration:.2f}秒")
    
    def log_update_progress(self, component: str, progress: float, status: str) -> None:
        """
        記錄更新進度
        
        Args:
            component: 組件名稱（yt-dlp/ffmpeg）
            progress: 更新進度（0-100）
            status: 更新狀態
        """
        self.info(f"更新進度 - 組件: {component}, 進度: {progress:.2f}%, 狀態: {status}")
    
    def log_update_complete(self, component: str, old_version: str, new_version: str) -> None:
        """
        記錄更新完成信息
        
        Args:
            component: 組件名稱（yt-dlp/ffmpeg）
            old_version: 舊版本
            new_version: 新版本
        """
        self.info(f"更新完成 - 組件: {component}, 版本: {old_version} -> {new_version}")
