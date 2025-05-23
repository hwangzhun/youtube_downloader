"""
YouTube Downloader 的日志管理模块
负责处理日志记录功能
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
    """日志管理类"""
    
    def __init__(self, log_file: str = None, log_level: int = logging.INFO):
        """
        初始化日志管理器
        
        Args:
            log_file: 日志文件路径，如果为 None 则使用默认路径
            log_level: 日志级别
        """
        # 获取应用程序数据目录
        if sys.platform.startswith('win'):
            app_data_dir = os.path.join(os.environ.get('APPDATA', ''), 'YouTubeDownloader', 'logs')
        else:
            app_data_dir = os.path.join(os.path.expanduser('~'), '.youtube_downloader', 'logs')
        
        # 确保目录存在
        os.makedirs(app_data_dir, exist_ok=True)
        
        # 设置日志文件路径
        self.log_file = log_file or os.path.join(
            app_data_dir, 
            f"youtube_downloader_{datetime.now().strftime('%Y%m%d')}.log"
        )
        
        # 创建日志记录器
        self.logger = logging.getLogger('youtube_downloader')
        self.logger.setLevel(log_level)
        
        # 清除现有处理器
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # 添加文件处理器
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        
        # 添加控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # 设置详细的日志格式
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        file_handler.setFormatter(detailed_formatter)
        console_handler.setFormatter(detailed_formatter)
        
        # 添加处理器到记录器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # 记录系统信息
        self._log_system_info()
    
    def _log_system_info(self):
        """记录系统信息"""
        system_info = self._get_system_info()
        self.info(f"系统信息: {system_info}")
    
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
        获取日志记录器
        
        Returns:
            日志记录器
        """
        return self.logger
    
    def debug(self, message: str) -> None:
        """
        记录调试信息
        
        Args:
            message: 日志信息
        """
        self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """
        记录一般信息
        
        Args:
            message: 日志信息
        """
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """
        记录警告信息
        
        Args:
            message: 日志信息
        """
        self.logger.warning(message)
    
    def error(self, message: str, exc_info: bool = True) -> None:
        """
        记录错误信息
        
        Args:
            message: 日志信息
            exc_info: 是否包含异常信息
        """
        if exc_info:
            self.logger.error(f"{message}\n{traceback.format_exc()}")
        else:
            self.logger.error(message)
    
    def critical(self, message: str, exc_info: bool = True) -> None:
        """
        记录严重错误信息
        
        Args:
            message: 日志信息
            exc_info: 是否包含异常信息
        """
        if exc_info:
            self.logger.critical(f"{message}\n{traceback.format_exc()}")
        else:
            self.logger.critical(message)
    
    def log_download_progress(self, url: str, progress: float, status: str) -> None:
        """
        记录下载进度
        
        Args:
            url: 视频URL
            progress: 下载进度（0-100）
            status: 下载状态
        """
        self.info(f"下载进度 - URL: {url}, 进度: {progress:.2f}%, 状态: {status}")
    
    def log_download_complete(self, url: str, output_path: str, duration: float) -> None:
        """
        记录下载完成信息
        
        Args:
            url: 视频URL
            output_path: 输出文件路径
            duration: 下载耗时（秒）
        """
        self.info(f"下载完成 - URL: {url}, 保存路径: {output_path}, 耗时: {duration:.2f}秒")
    
    def log_update_progress(self, component: str, progress: float, status: str) -> None:
        """
        记录更新进度
        
        Args:
            component: 组件名称（yt-dlp/ffmpeg）
            progress: 更新进度（0-100）
            status: 更新状态
        """
        self.info(f"更新进度 - 组件: {component}, 进度: {progress:.2f}%, 状态: {status}")
    
    def log_update_complete(self, component: str, old_version: str, new_version: str) -> None:
        """
        记录更新完成信息
        
        Args:
            component: 组件名称（yt-dlp/ffmpeg）
            old_version: 旧版本
            new_version: 新版本
        """
        self.info(f"更新完成 - 组件: {component}, 版本: {old_version} -> {new_version}")
