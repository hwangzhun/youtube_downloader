"""
YouTube 視頻下載工具的日誌管理模塊
負責處理日誌記錄功能
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime


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
            backupCount=5
        )
        file_handler.setLevel(log_level)
        
        # 添加控制台處理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # 設置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加處理器到記錄器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
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
    
    def error(self, message: str) -> None:
        """
        記錄錯誤信息
        
        Args:
            message: 日誌信息
        """
        self.logger.error(message)
    
    def critical(self, message: str) -> None:
        """
        記錄嚴重錯誤信息
        
        Args:
            message: 日誌信息
        """
        self.logger.critical(message)
