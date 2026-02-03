"""
YouTube Downloader 临时文件管理模块
统一管理临时文件的创建和清理
"""
import os
import tempfile
import shutil
import atexit
import threading
from typing import Optional, List, Set
from pathlib import Path
from datetime import datetime, timedelta

from src.utils.platform import get_cache_dir
from src.utils.logger import LoggerManager


class TempFileManager:
    """
    临时文件管理器
    
    特性：
    - 统一临时文件创建
    - 自动清理
    - 跟踪所有临时文件
    - 安全删除选项
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.logger = LoggerManager().get_logger()
        
        # 临时目录
        self._temp_dir: Optional[str] = None
        
        # 跟踪的临时文件
        self._temp_files: Set[str] = set()
        self._temp_dirs: Set[str] = set()
        self._lock = threading.RLock()
        
        # 注册退出清理
        atexit.register(self.cleanup_all)
        
        self.logger.info("临时文件管理器初始化完成")
    
    def _get_temp_dir(self) -> str:
        """获取临时目录"""
        if self._temp_dir is None:
            self._temp_dir = str(get_cache_dir() / 'temp')
            os.makedirs(self._temp_dir, exist_ok=True)
        return self._temp_dir
    
    def create_temp_file(
        self,
        suffix: str = '',
        prefix: str = 'ytdl_',
        dir: Optional[str] = None,
        delete_on_exit: bool = True
    ) -> str:
        """
        创建临时文件
        
        Args:
            suffix: 文件后缀
            prefix: 文件前缀
            dir: 目录（默认使用应用临时目录）
            delete_on_exit: 是否在退出时删除
            
        Returns:
            临时文件路径
        """
        temp_dir = dir or self._get_temp_dir()
        
        fd, temp_path = tempfile.mkstemp(
            suffix=suffix,
            prefix=prefix,
            dir=temp_dir
        )
        os.close(fd)
        
        if delete_on_exit:
            with self._lock:
                self._temp_files.add(temp_path)
        
        self.logger.debug(f"创建临时文件: {temp_path}")
        return temp_path
    
    def create_temp_dir(
        self,
        suffix: str = '',
        prefix: str = 'ytdl_',
        dir: Optional[str] = None,
        delete_on_exit: bool = True
    ) -> str:
        """
        创建临时目录
        
        Args:
            suffix: 目录后缀
            prefix: 目录前缀
            dir: 父目录（默认使用应用临时目录）
            delete_on_exit: 是否在退出时删除
            
        Returns:
            临时目录路径
        """
        temp_dir = dir or self._get_temp_dir()
        
        temp_path = tempfile.mkdtemp(
            suffix=suffix,
            prefix=prefix,
            dir=temp_dir
        )
        
        if delete_on_exit:
            with self._lock:
                self._temp_dirs.add(temp_path)
        
        self.logger.debug(f"创建临时目录: {temp_path}")
        return temp_path
    
    def register_file(self, file_path: str):
        """
        注册外部创建的临时文件
        
        Args:
            file_path: 文件路径
        """
        with self._lock:
            self._temp_files.add(file_path)
    
    def register_dir(self, dir_path: str):
        """
        注册外部创建的临时目录
        
        Args:
            dir_path: 目录路径
        """
        with self._lock:
            self._temp_dirs.add(dir_path)
    
    def unregister_file(self, file_path: str):
        """取消注册文件"""
        with self._lock:
            self._temp_files.discard(file_path)
    
    def unregister_dir(self, dir_path: str):
        """取消注册目录"""
        with self._lock:
            self._temp_dirs.discard(dir_path)
    
    def delete_file(self, file_path: str, secure: bool = False) -> bool:
        """
        删除临时文件
        
        Args:
            file_path: 文件路径
            secure: 是否安全删除（覆写后删除）
            
        Returns:
            是否成功删除
        """
        try:
            if not os.path.exists(file_path):
                self.unregister_file(file_path)
                return True
            
            if secure:
                self._secure_delete(file_path)
            else:
                os.remove(file_path)
            
            self.unregister_file(file_path)
            self.logger.debug(f"删除临时文件: {file_path}")
            return True
        except Exception as e:
            self.logger.warning(f"删除临时文件失败: {file_path} - {e}")
            return False
    
    def delete_dir(self, dir_path: str) -> bool:
        """
        删除临时目录
        
        Args:
            dir_path: 目录路径
            
        Returns:
            是否成功删除
        """
        try:
            if not os.path.exists(dir_path):
                self.unregister_dir(dir_path)
                return True
            
            shutil.rmtree(dir_path, ignore_errors=True)
            self.unregister_dir(dir_path)
            self.logger.debug(f"删除临时目录: {dir_path}")
            return True
        except Exception as e:
            self.logger.warning(f"删除临时目录失败: {dir_path} - {e}")
            return False
    
    def _secure_delete(self, file_path: str):
        """
        安全删除文件（覆写后删除）
        
        Args:
            file_path: 文件路径
        """
        try:
            file_size = os.path.getsize(file_path)
            
            # 用随机数据覆写
            with open(file_path, 'wb') as f:
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())
            
            os.remove(file_path)
        except Exception:
            # 如果安全删除失败，尝试普通删除
            os.remove(file_path)
    
    def cleanup_all(self):
        """清理所有临时文件和目录"""
        with self._lock:
            # 清理文件
            for file_path in list(self._temp_files):
                self.delete_file(file_path)
            
            # 清理目录
            for dir_path in list(self._temp_dirs):
                self.delete_dir(dir_path)
            
            # 清理主临时目录中的旧文件
            self._cleanup_old_files()
        
        self.logger.info("临时文件清理完成")
    
    def _cleanup_old_files(self, max_age_hours: int = 24):
        """
        清理旧的临时文件
        
        Args:
            max_age_hours: 最大保留时间（小时）
        """
        temp_dir = self._get_temp_dir()
        if not os.path.exists(temp_dir):
            return
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        try:
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                try:
                    stat = os.stat(item_path)
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    
                    if mtime < cutoff_time:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path, ignore_errors=True)
                        self.logger.debug(f"清理旧临时文件: {item_path}")
                except Exception:
                    pass
        except Exception as e:
            self.logger.warning(f"清理旧临时文件时出错: {e}")
    
    def get_temp_file_count(self) -> int:
        """获取跟踪的临时文件数量"""
        with self._lock:
            return len(self._temp_files)
    
    def get_temp_dir_count(self) -> int:
        """获取跟踪的临时目录数量"""
        with self._lock:
            return len(self._temp_dirs)
    
    def get_temp_size(self) -> int:
        """
        获取临时文件总大小
        
        Returns:
            总大小（字节）
        """
        total_size = 0
        with self._lock:
            for file_path in self._temp_files:
                try:
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
                except Exception:
                    pass
        return total_size
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            'temp_files': self.get_temp_file_count(),
            'temp_dirs': self.get_temp_dir_count(),
            'total_size': self.get_temp_size(),
            'temp_dir': self._get_temp_dir()
        }


# 全局实例
temp_manager = TempFileManager()


# 便捷函数
def create_temp_file(**kwargs) -> str:
    """创建临时文件"""
    return temp_manager.create_temp_file(**kwargs)


def create_temp_dir(**kwargs) -> str:
    """创建临时目录"""
    return temp_manager.create_temp_dir(**kwargs)


def delete_temp_file(file_path: str, secure: bool = False) -> bool:
    """删除临时文件"""
    return temp_manager.delete_file(file_path, secure)


def cleanup_temp_files():
    """清理所有临时文件"""
    temp_manager.cleanup_all()

