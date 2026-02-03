"""
YouTube Downloader 下载历史记录模块
提供下载历史的记录、查询和管理功能
"""
import os
import json
import sqlite3
import threading
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager

from src.utils.platform import get_app_data_dir
from src.utils.logger import LoggerManager
from src.core.event_bus import event_bus, Events
from src.types import DownloadStatus


@dataclass
class HistoryRecord:
    """历史记录"""
    id: str                           # 记录 ID
    url: str                          # 视频 URL
    title: str                        # 视频标题
    file_path: str                    # 文件路径
    format: str                       # 格式
    size: int = 0                     # 文件大小（字节）
    duration: int = 0                 # 时长（秒）
    thumbnail: str = ""               # 缩略图 URL
    uploader: str = ""                # 上传者
    status: str = "completed"         # 状态
    error_message: str = ""           # 错误信息
    downloaded_at: str = ""           # 下载时间
    created_at: str = ""              # 创建时间
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.downloaded_at:
            self.downloaded_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HistoryRecord':
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def file_exists(self) -> bool:
        """检查文件是否存在"""
        return os.path.exists(self.file_path)
    
    def get_file_size_str(self) -> str:
        """获取格式化的文件大小"""
        if self.size <= 0:
            return "未知"
        
        size = float(self.size)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"


class DownloadHistory:
    """
    下载历史管理器
    
    特性：
    - SQLite 持久化存储
    - 自动记录下载完成事件
    - 搜索和过滤
    - 历史清理
    """
    
    def __init__(self, db_path: Optional[str] = None, auto_subscribe: bool = True):
        """
        初始化下载历史管理器
        
        Args:
            db_path: 数据库路径
            auto_subscribe: 是否自动订阅下载完成事件
        """
        self.logger = LoggerManager().get_logger()
        self.db_path = db_path or str(get_app_data_dir() / 'history.db')
        self._lock = threading.RLock()
        
        # 初始化数据库
        self._init_db()
        
        # 订阅下载完成事件
        if auto_subscribe:
            event_bus.subscribe(Events.DOWNLOAD_COMPLETED, self._on_download_completed)
            event_bus.subscribe(Events.DOWNLOAD_FAILED, self._on_download_failed)
        
        self.logger.info(f"下载历史管理器初始化完成: {self.db_path}")
    
    def _init_db(self):
        """初始化数据库"""
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS history (
                        id TEXT PRIMARY KEY,
                        url TEXT NOT NULL,
                        title TEXT NOT NULL,
                        file_path TEXT,
                        format TEXT,
                        size INTEGER DEFAULT 0,
                        duration INTEGER DEFAULT 0,
                        thumbnail TEXT,
                        uploader TEXT,
                        status TEXT DEFAULT 'completed',
                        error_message TEXT,
                        downloaded_at TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                ''')
                
                # 创建索引
                conn.execute('CREATE INDEX IF NOT EXISTS idx_history_url ON history(url)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_history_downloaded_at ON history(downloaded_at)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_history_status ON history(status)')
                
                conn.commit()
        except Exception as e:
            self.logger.error(f"初始化历史数据库失败: {e}")
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _on_download_completed(self, event):
        """处理下载完成事件"""
        try:
            data = event.data
            record = HistoryRecord(
                id=data.get('task_id', ''),
                url=data.get('url', ''),
                title=data.get('title', '未知标题'),
                file_path=data.get('file_path', ''),
                format=data.get('format', ''),
                size=data.get('size', 0),
                duration=data.get('duration', 0),
                thumbnail=data.get('thumbnail', ''),
                uploader=data.get('uploader', ''),
                status='completed'
            )
            self.add(record)
        except Exception as e:
            self.logger.error(f"记录下载历史失败: {e}")
    
    def _on_download_failed(self, event):
        """处理下载失败事件"""
        try:
            data = event.data
            record = HistoryRecord(
                id=data.get('task_id', ''),
                url=data.get('url', ''),
                title=data.get('title', '未知标题'),
                file_path='',
                format='',
                status='failed',
                error_message=data.get('error', '')
            )
            self.add(record)
        except Exception as e:
            self.logger.error(f"记录下载失败历史失败: {e}")
    
    def add(self, record: HistoryRecord) -> bool:
        """
        添加历史记录
        
        Args:
            record: 历史记录
            
        Returns:
            是否成功添加
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO history 
                        (id, url, title, file_path, format, size, duration, 
                         thumbnail, uploader, status, error_message, downloaded_at, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        record.id, record.url, record.title, record.file_path,
                        record.format, record.size, record.duration, record.thumbnail,
                        record.uploader, record.status, record.error_message,
                        record.downloaded_at, record.created_at
                    ))
                    conn.commit()
                return True
            except Exception as e:
                self.logger.error(f"添加历史记录失败: {e}")
                return False
    
    def get(self, record_id: str) -> Optional[HistoryRecord]:
        """
        获取历史记录
        
        Args:
            record_id: 记录 ID
            
        Returns:
            历史记录或 None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    'SELECT * FROM history WHERE id = ?',
                    (record_id,)
                )
                row = cursor.fetchone()
                if row:
                    return HistoryRecord.from_dict(dict(row))
                return None
        except Exception as e:
            self.logger.error(f"获取历史记录失败: {e}")
            return None
    
    def get_all(
        self, 
        limit: int = 100, 
        offset: int = 0,
        status: Optional[str] = None,
        order_by: str = 'downloaded_at',
        order_desc: bool = True
    ) -> List[HistoryRecord]:
        """
        获取所有历史记录
        
        Args:
            limit: 限制数量
            offset: 偏移量
            status: 状态过滤
            order_by: 排序字段
            order_desc: 是否降序
            
        Returns:
            历史记录列表
        """
        try:
            with self._get_connection() as conn:
                order = 'DESC' if order_desc else 'ASC'
                
                if status:
                    cursor = conn.execute(
                        f'SELECT * FROM history WHERE status = ? ORDER BY {order_by} {order} LIMIT ? OFFSET ?',
                        (status, limit, offset)
                    )
                else:
                    cursor = conn.execute(
                        f'SELECT * FROM history ORDER BY {order_by} {order} LIMIT ? OFFSET ?',
                        (limit, offset)
                    )
                
                return [HistoryRecord.from_dict(dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"获取历史记录列表失败: {e}")
            return []
    
    def search(
        self, 
        query: str, 
        limit: int = 50
    ) -> List[HistoryRecord]:
        """
        搜索历史记录
        
        Args:
            query: 搜索关键词
            limit: 限制数量
            
        Returns:
            匹配的历史记录列表
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    '''SELECT * FROM history 
                       WHERE title LIKE ? OR url LIKE ? OR uploader LIKE ?
                       ORDER BY downloaded_at DESC
                       LIMIT ?''',
                    (f'%{query}%', f'%{query}%', f'%{query}%', limit)
                )
                return [HistoryRecord.from_dict(dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"搜索历史记录失败: {e}")
            return []
    
    def get_by_url(self, url: str) -> Optional[HistoryRecord]:
        """
        根据 URL 获取最近的历史记录
        
        Args:
            url: 视频 URL
            
        Returns:
            历史记录或 None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    'SELECT * FROM history WHERE url = ? ORDER BY downloaded_at DESC LIMIT 1',
                    (url,)
                )
                row = cursor.fetchone()
                if row:
                    return HistoryRecord.from_dict(dict(row))
                return None
        except Exception as e:
            self.logger.error(f"根据URL获取历史记录失败: {e}")
            return None
    
    def delete(self, record_id: str) -> bool:
        """
        删除历史记录
        
        Args:
            record_id: 记录 ID
            
        Returns:
            是否成功删除
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        'DELETE FROM history WHERE id = ?',
                        (record_id,)
                    )
                    conn.commit()
                    return cursor.rowcount > 0
            except Exception as e:
                self.logger.error(f"删除历史记录失败: {e}")
                return False
    
    def delete_before(self, before_date: datetime) -> int:
        """
        删除指定日期之前的记录
        
        Args:
            before_date: 日期
            
        Returns:
            删除的记录数
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        'DELETE FROM history WHERE downloaded_at < ?',
                        (before_date.isoformat(),)
                    )
                    conn.commit()
                    count = cursor.rowcount
                    self.logger.info(f"已删除 {count} 条历史记录")
                    return count
            except Exception as e:
                self.logger.error(f"删除历史记录失败: {e}")
                return 0
    
    def clear(self) -> bool:
        """
        清空所有历史记录
        
        Returns:
            是否成功清空
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute('DELETE FROM history')
                    conn.commit()
                self.logger.info("已清空所有历史记录")
                return True
            except Exception as e:
                self.logger.error(f"清空历史记录失败: {e}")
                return False
    
    def get_count(self, status: Optional[str] = None) -> int:
        """
        获取记录数量
        
        Args:
            status: 状态过滤
            
        Returns:
            记录数量
        """
        try:
            with self._get_connection() as conn:
                if status:
                    cursor = conn.execute(
                        'SELECT COUNT(*) FROM history WHERE status = ?',
                        (status,)
                    )
                else:
                    cursor = conn.execute('SELECT COUNT(*) FROM history')
                return cursor.fetchone()[0]
        except Exception as e:
            self.logger.error(f"获取历史记录数量失败: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        try:
            with self._get_connection() as conn:
                # 总数
                total = conn.execute('SELECT COUNT(*) FROM history').fetchone()[0]
                
                # 成功数
                completed = conn.execute(
                    'SELECT COUNT(*) FROM history WHERE status = ?',
                    ('completed',)
                ).fetchone()[0]
                
                # 失败数
                failed = conn.execute(
                    'SELECT COUNT(*) FROM history WHERE status = ?',
                    ('failed',)
                ).fetchone()[0]
                
                # 总大小
                total_size = conn.execute(
                    'SELECT SUM(size) FROM history WHERE status = ?',
                    ('completed',)
                ).fetchone()[0] or 0
                
                # 今日下载数
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                today_count = conn.execute(
                    'SELECT COUNT(*) FROM history WHERE downloaded_at >= ?',
                    (today.isoformat(),)
                ).fetchone()[0]
                
                return {
                    'total': total,
                    'completed': completed,
                    'failed': failed,
                    'total_size': total_size,
                    'today_count': today_count
                }
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {
                'total': 0,
                'completed': 0,
                'failed': 0,
                'total_size': 0,
                'today_count': 0
            }
    
    def cleanup_old(self, days: int = 30) -> int:
        """
        清理旧记录
        
        Args:
            days: 保留天数
            
        Returns:
            删除的记录数
        """
        before_date = datetime.now() - timedelta(days=days)
        return self.delete_before(before_date)
    
    def export_to_json(self, file_path: str) -> bool:
        """
        导出到 JSON 文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功导出
        """
        try:
            records = self.get_all(limit=10000)
            data = [record.to_dict() for record in records]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"已导出 {len(records)} 条历史记录到 {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"导出历史记录失败: {e}")
            return False
    
    def import_from_json(self, file_path: str) -> int:
        """
        从 JSON 文件导入
        
        Args:
            file_path: 文件路径
            
        Returns:
            导入的记录数
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            count = 0
            for item in data:
                record = HistoryRecord.from_dict(item)
                if self.add(record):
                    count += 1
            
            self.logger.info(f"已导入 {count} 条历史记录")
            return count
        except Exception as e:
            self.logger.error(f"导入历史记录失败: {e}")
            return 0


# 创建全局下载历史实例
download_history = DownloadHistory()

