"""
YouTube Downloader 统一缓存管理模块
实现双层缓存：内存 LRU + SQLite 持久化
"""
import os
import json
import sqlite3
import hashlib
import threading
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from functools import lru_cache
from contextlib import contextmanager
from pathlib import Path

from src.utils.platform import get_cache_dir
from src.utils.logger import LoggerManager


class CacheEntry:
    """缓存条目"""
    
    def __init__(
        self, 
        key: str, 
        value: Any, 
        expires_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None
    ):
        self.key = key
        self.value = value
        self.created_at = created_at or datetime.now()
        self.expires_at = expires_at
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'key': self.key,
            'value': self.value,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CacheEntry':
        """从字典创建"""
        expires_at = None
        if data.get('expires_at'):
            expires_at = datetime.fromisoformat(data['expires_at'])
        
        return cls(
            key=data['key'],
            value=data['value'],
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=expires_at
        )


class MemoryCache:
    """内存缓存（LRU）"""
    
    def __init__(self, max_size: int = 100):
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: list = []
        self._max_size = max_size
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            if entry.is_expired():
                self.delete(key)
                return None
            
            # 更新访问顺序（LRU）
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            return entry.value
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None
    ):
        """设置缓存值"""
        with self._lock:
            # 检查容量
            while len(self._cache) >= self._max_size:
                self._evict_oldest()
            
            expires_at = None
            if ttl_seconds:
                expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
            
            entry = CacheEntry(key, value, expires_at)
            self._cache[key] = entry
            
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return True
            return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            if entry.is_expired():
                self.delete(key)
                return False
            return True
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def _evict_oldest(self):
        """驱逐最旧的条目"""
        if self._access_order:
            oldest_key = self._access_order.pop(0)
            self._cache.pop(oldest_key, None)
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)


class SQLiteCache:
    """SQLite 持久化缓存"""
    
    def __init__(self, db_path: Optional[str] = None, table_name: str = "cache"):
        self.db_path = db_path or str(get_cache_dir() / 'cache.db')
        self.table_name = table_name
        self._lock = threading.RLock()
        self.logger = LoggerManager().get_logger()
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        try:
            with self._get_connection() as conn:
                conn.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        expires_at TEXT,
                        updated_at TEXT NOT NULL
                    )
                ''')
                conn.execute(f'''
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_expires 
                    ON {self.table_name}(expires_at)
                ''')
                conn.commit()
        except Exception as e:
            self.logger.error(f"初始化缓存数据库失败: {e}")
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        f'''SELECT value, expires_at FROM {self.table_name} 
                           WHERE key = ?''',
                        (key,)
                    )
                    row = cursor.fetchone()
                    
                    if row is None:
                        return None
                    
                    # 检查过期
                    if row['expires_at']:
                        expires_at = datetime.fromisoformat(row['expires_at'])
                        if datetime.now() > expires_at:
                            self.delete(key)
                            return None
                    
                    return json.loads(row['value'])
            except Exception as e:
                self.logger.error(f"读取缓存失败: {e}")
                return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None
    ):
        """设置缓存值"""
        with self._lock:
            try:
                now = datetime.now().isoformat()
                expires_at = None
                if ttl_seconds:
                    expires_at = (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat()
                
                value_json = json.dumps(value, ensure_ascii=False)
                
                with self._get_connection() as conn:
                    conn.execute(
                        f'''INSERT OR REPLACE INTO {self.table_name} 
                           (key, value, created_at, expires_at, updated_at)
                           VALUES (?, ?, ?, ?, ?)''',
                        (key, value_json, now, expires_at, now)
                    )
                    conn.commit()
            except Exception as e:
                self.logger.error(f"写入缓存失败: {e}")
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        f'DELETE FROM {self.table_name} WHERE key = ?',
                        (key,)
                    )
                    conn.commit()
                    return cursor.rowcount > 0
            except Exception as e:
                self.logger.error(f"删除缓存失败: {e}")
                return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return self.get(key) is not None
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute(f'DELETE FROM {self.table_name}')
                    conn.commit()
            except Exception as e:
                self.logger.error(f"清空缓存失败: {e}")
    
    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    now = datetime.now().isoformat()
                    cursor = conn.execute(
                        f'''DELETE FROM {self.table_name} 
                           WHERE expires_at IS NOT NULL AND expires_at < ?''',
                        (now,)
                    )
                    conn.commit()
                    return cursor.rowcount
            except Exception as e:
                self.logger.error(f"清理过期缓存失败: {e}")
                return 0
    
    def size(self) -> int:
        """获取缓存大小"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(f'SELECT COUNT(*) FROM {self.table_name}')
                return cursor.fetchone()[0]
        except Exception:
            return 0


class TwoLevelCache:
    """双层缓存：内存 + SQLite"""
    
    def __init__(
        self,
        name: str = "default",
        memory_max_size: int = 100,
        default_ttl: Optional[int] = 3600 * 24,  # 默认 24 小时
    ):
        self.name = name
        self.default_ttl = default_ttl
        self._memory = MemoryCache(max_size=memory_max_size)
        self._sqlite = SQLiteCache(table_name=f"cache_{name}")
        self.logger = LoggerManager().get_logger()
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        先查内存，再查 SQLite，命中后回填内存
        """
        # 先查内存
        value = self._memory.get(key)
        if value is not None:
            return value
        
        # 再查 SQLite
        value = self._sqlite.get(key)
        if value is not None:
            # 回填内存
            self._memory.set(key, value, self.default_ttl)
            return value
        
        return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None
    ):
        """设置缓存值（同时写入内存和 SQLite）"""
        ttl = ttl_seconds or self.default_ttl
        self._memory.set(key, value, ttl)
        self._sqlite.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        m = self._memory.delete(key)
        s = self._sqlite.delete(key)
        return m or s
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return self._memory.exists(key) or self._sqlite.exists(key)
    
    def clear(self):
        """清空缓存"""
        self._memory.clear()
        self._sqlite.clear()
    
    def cleanup(self) -> int:
        """清理过期缓存"""
        return self._sqlite.cleanup_expired()
    
    def get_or_set(
        self, 
        key: str, 
        factory: Callable[[], Any],
        ttl_seconds: Optional[int] = None
    ) -> Any:
        """
        获取缓存值，如果不存在则调用 factory 生成并缓存
        
        Args:
            key: 缓存键
            factory: 生成值的工厂函数
            ttl_seconds: 过期时间（秒）
        """
        value = self.get(key)
        if value is not None:
            return value
        
        value = factory()
        if value is not None:
            self.set(key, value, ttl_seconds)
        
        return value


# ============ 缓存工具函数 ============

def make_cache_key(*args, **kwargs) -> str:
    """
    生成缓存键
    
    将参数转换为稳定的哈希键
    """
    key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True)
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(
    cache: TwoLevelCache,
    key_prefix: str = "",
    ttl_seconds: Optional[int] = None
):
    """
    缓存装饰器
    
    Example:
        video_cache = TwoLevelCache("video_info")
        
        @cached(video_cache, "video_info", ttl_seconds=3600)
        def get_video_info(url):
            ...
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key = f"{key_prefix}:{make_cache_key(*args, **kwargs)}"
            
            # 尝试获取缓存
            value = cache.get(key)
            if value is not None:
                return value
            
            # 调用函数
            value = func(*args, **kwargs)
            
            # 缓存结果
            if value is not None:
                cache.set(key, value, ttl_seconds)
            
            return value
        return wrapper
    return decorator


# ============ 预定义缓存实例 ============

# 视频信息缓存
video_info_cache = TwoLevelCache(
    name="video_info",
    memory_max_size=50,
    default_ttl=3600 * 24  # 24 小时
)

# 格式信息缓存
format_cache = TwoLevelCache(
    name="format",
    memory_max_size=100,
    default_ttl=3600 * 6  # 6 小时
)

# 版本信息缓存
version_cache = TwoLevelCache(
    name="version",
    memory_max_size=10,
    default_ttl=3600  # 1 小时
)

