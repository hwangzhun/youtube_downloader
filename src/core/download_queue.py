"""
YouTube Downloader 下载队列管理模块
提供任务排队、优先级和并发控制功能
"""
import threading
import queue
from typing import Optional, List, Dict, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import uuid

from src.utils.logger import LoggerManager
from src.core.event_bus import event_bus, Events
from src.types import DownloadStatus, DownloadPriority, DownloadOptions


@dataclass(order=True)
class QueuedTask:
    """队列任务"""
    priority: int = field(compare=True)  # 用于优先级队列排序
    created_at: datetime = field(compare=True, default_factory=datetime.now)
    
    # 以下字段不参与比较
    id: str = field(compare=False, default_factory=lambda: str(uuid.uuid4()))
    url: str = field(compare=False, default="")
    title: str = field(compare=False, default="")
    output_dir: str = field(compare=False, default="")
    video_format_id: str = field(compare=False, default="best")
    audio_format_id: str = field(compare=False, default="best")
    use_cookies: bool = field(compare=False, default=False)
    cookies_file: Optional[str] = field(compare=False, default=None)
    prefer_mp4: bool = field(compare=False, default=True)
    no_playlist: bool = field(compare=False, default=True)
    proxy_url: Optional[str] = field(compare=False, default=None)
    status: DownloadStatus = field(compare=False, default=DownloadStatus.PENDING)
    progress: float = field(compare=False, default=0.0)
    speed: str = field(compare=False, default="")
    eta: str = field(compare=False, default="")
    error_message: str = field(compare=False, default="")
    file_path: str = field(compare=False, default="")
    started_at: Optional[datetime] = field(compare=False, default=None)
    completed_at: Optional[datetime] = field(compare=False, default=None)
    
    @classmethod
    def from_options(cls, options: DownloadOptions, priority: DownloadPriority = DownloadPriority.NORMAL) -> 'QueuedTask':
        """从下载选项创建队列任务"""
        return cls(
            priority=priority.value,
            url=options.url,
            output_dir=options.output_dir,
            video_format_id=options.video_format_id,
            audio_format_id=options.audio_format_id,
            use_cookies=options.use_cookies,
            cookies_file=options.cookies_file,
            prefer_mp4=options.prefer_mp4,
            no_playlist=options.no_playlist
        )
    
    def get_format_id(self) -> str:
        """获取合并的格式ID"""
        if self.audio_format_id and self.audio_format_id != "best":
            return f"{self.video_format_id}+{self.audio_format_id}"
        return self.video_format_id


class DownloadQueue:
    """
    下载队列管理器
    
    特性：
    - 优先级队列
    - 并发控制
    - 暂停/恢复
    - 任务持久化（可选）
    """
    
    def __init__(self, max_concurrent: int = 2, auto_start: bool = True):
        """
        初始化下载队列
        
        Args:
            max_concurrent: 最大并发下载数
            auto_start: 是否自动开始队列处理
        """
        self.logger = LoggerManager().get_logger()
        self.max_concurrent = max_concurrent
        self.auto_start = auto_start
        
        # 队列和任务管理
        self._queue: queue.PriorityQueue = queue.PriorityQueue()
        self._tasks: Dict[str, QueuedTask] = {}
        self._active_tasks: Dict[str, threading.Thread] = {}
        self._lock = threading.RLock()
        
        # 状态
        self._running = False
        self._paused = False
        self._worker_thread: Optional[threading.Thread] = None
        
        # 下载器回调
        self._download_callback: Optional[Callable[[QueuedTask], None]] = None
        
        self.logger.info(f"下载队列初始化完成，最大并发: {max_concurrent}")
    
    def set_download_callback(self, callback: Callable[[QueuedTask], None]):
        """
        设置下载回调函数
        
        Args:
            callback: 下载回调，接收 QueuedTask 参数
        """
        self._download_callback = callback
    
    def add(
        self, 
        options: DownloadOptions, 
        priority: DownloadPriority = DownloadPriority.NORMAL,
        title: str = ""
    ) -> str:
        """
        添加任务到队列
        
        Args:
            options: 下载选项
            priority: 优先级
            title: 视频标题（可选）
            
        Returns:
            任务 ID
        """
        task = QueuedTask.from_options(options, priority)
        task.title = title
        
        with self._lock:
            self._tasks[task.id] = task
            self._queue.put(task)
        
        self.logger.info(f"任务加入队列: {task.id} - {task.url}")
        
        # 发布事件
        event_bus.emit(Events.QUEUE_TASK_ADDED, task_id=task.id, url=task.url)
        
        # 自动开始
        if self.auto_start and not self._running:
            self.start()
        
        return task.id
    
    def add_batch(
        self, 
        options_list: List[DownloadOptions],
        priority: DownloadPriority = DownloadPriority.NORMAL
    ) -> List[str]:
        """
        批量添加任务
        
        Args:
            options_list: 下载选项列表
            priority: 优先级
            
        Returns:
            任务 ID 列表
        """
        task_ids = []
        for options in options_list:
            task_id = self.add(options, priority)
            task_ids.append(task_id)
        return task_ids
    
    def remove(self, task_id: str) -> bool:
        """
        从队列中移除任务（仅限未开始的任务）
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否成功移除
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            if task.status in (DownloadStatus.DOWNLOADING,):
                self.logger.warning(f"无法移除正在下载的任务: {task_id}")
                return False
            
            # 标记为已取消
            task.status = DownloadStatus.CANCELLED
            
            # 发布事件
            event_bus.emit(Events.QUEUE_TASK_REMOVED, task_id=task_id)
            
            self.logger.info(f"任务已移除: {task_id}")
            return True
    
    def start(self):
        """开始处理队列"""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._paused = False
            
            self._worker_thread = threading.Thread(
                target=self._process_queue,
                daemon=True
            )
            self._worker_thread.start()
        
        event_bus.emit(Events.QUEUE_STARTED)
        self.logger.info("队列处理已开始")
    
    def stop(self):
        """停止处理队列"""
        with self._lock:
            if not self._running:
                return
            
            self._running = False
        
        # 等待工作线程结束
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        
        event_bus.emit(Events.QUEUE_STOPPED)
        self.logger.info("队列处理已停止")
    
    def pause(self):
        """暂停队列处理"""
        with self._lock:
            self._paused = True
        self.logger.info("队列处理已暂停")
    
    def resume(self):
        """恢复队列处理"""
        with self._lock:
            self._paused = False
        self.logger.info("队列处理已恢复")
    
    def _process_queue(self):
        """队列处理线程"""
        while self._running:
            try:
                # 检查是否暂停
                if self._paused:
                    threading.Event().wait(0.5)
                    continue
                
                # 检查并发限制
                with self._lock:
                    if len(self._active_tasks) >= self.max_concurrent:
                        threading.Event().wait(0.5)
                        continue
                
                # 获取下一个任务
                try:
                    task = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # 检查任务状态
                if task.status == DownloadStatus.CANCELLED:
                    continue
                
                # 开始下载
                self._start_task(task)
                
            except Exception as e:
                self.logger.error(f"队列处理错误: {e}")
    
    def _start_task(self, task: QueuedTask):
        """开始任务"""
        with self._lock:
            task.status = DownloadStatus.DOWNLOADING
            task.started_at = datetime.now()
            
            thread = threading.Thread(
                target=self._execute_task,
                args=(task,),
                daemon=True
            )
            self._active_tasks[task.id] = thread
            thread.start()
        
        event_bus.emit(Events.DOWNLOAD_STARTED, task_id=task.id, url=task.url)
        self.logger.info(f"任务开始下载: {task.id}")
    
    def _execute_task(self, task: QueuedTask):
        """执行任务"""
        try:
            if self._download_callback:
                self._download_callback(task)
            else:
                self.logger.warning("未设置下载回调，任务无法执行")
                task.status = DownloadStatus.FAILED
                task.error_message = "未设置下载回调"
            
        except Exception as e:
            task.status = DownloadStatus.FAILED
            task.error_message = str(e)
            self.logger.error(f"任务执行失败: {task.id} - {e}")
            
        finally:
            with self._lock:
                self._active_tasks.pop(task.id, None)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            task.status = DownloadStatus.CANCELLED
            event_bus.emit(Events.DOWNLOAD_CANCELLED, task_id=task_id)
            return True
    
    def get_task(self, task_id: str) -> Optional[QueuedTask]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[QueuedTask]:
        """获取所有任务"""
        return list(self._tasks.values())
    
    def get_pending_tasks(self) -> List[QueuedTask]:
        """获取等待中的任务"""
        return [t for t in self._tasks.values() if t.status == DownloadStatus.PENDING]
    
    def get_active_tasks(self) -> List[QueuedTask]:
        """获取活跃任务"""
        return [t for t in self._tasks.values() if t.status == DownloadStatus.DOWNLOADING]
    
    def get_completed_tasks(self) -> List[QueuedTask]:
        """获取已完成任务"""
        return [t for t in self._tasks.values() if t.status == DownloadStatus.COMPLETED]
    
    def get_failed_tasks(self) -> List[QueuedTask]:
        """获取失败任务"""
        return [t for t in self._tasks.values() if t.status == DownloadStatus.FAILED]
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self._queue.qsize()
    
    def get_active_count(self) -> int:
        """获取活跃任务数"""
        return len(self._active_tasks)
    
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
    
    def is_paused(self) -> bool:
        """是否已暂停"""
        return self._paused
    
    def clear_completed(self):
        """清除已完成的任务"""
        with self._lock:
            to_remove = [
                tid for tid, task in self._tasks.items()
                if task.status in (DownloadStatus.COMPLETED, DownloadStatus.CANCELLED, DownloadStatus.FAILED)
            ]
            for tid in to_remove:
                del self._tasks[tid]
        
        self.logger.info(f"已清除 {len(to_remove)} 个已完成的任务")
    
    def clear_all(self):
        """清除所有任务（包括取消活跃任务）"""
        with self._lock:
            # 取消所有活跃任务
            for task_id in list(self._active_tasks.keys()):
                self.cancel_task(task_id)
            
            # 清空队列
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
            
            # 清空任务字典
            self._tasks.clear()
        
        event_bus.emit(Events.QUEUE_CLEARED)
        self.logger.info("已清除所有任务")
    
    def update_priority(self, task_id: str, priority: DownloadPriority) -> bool:
        """
        更新任务优先级（仅限未开始的任务）
        
        Args:
            task_id: 任务 ID
            priority: 新优先级
            
        Returns:
            是否成功更新
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            if task.status != DownloadStatus.PENDING:
                return False
            
            task.priority = priority.value
            return True
    
    def get_statistics(self) -> Dict[str, int]:
        """获取队列统计信息"""
        with self._lock:
            stats = {
                'total': len(self._tasks),
                'pending': 0,
                'downloading': 0,
                'completed': 0,
                'failed': 0,
                'cancelled': 0
            }
            
            for task in self._tasks.values():
                if task.status == DownloadStatus.PENDING:
                    stats['pending'] += 1
                elif task.status == DownloadStatus.DOWNLOADING:
                    stats['downloading'] += 1
                elif task.status == DownloadStatus.COMPLETED:
                    stats['completed'] += 1
                elif task.status == DownloadStatus.FAILED:
                    stats['failed'] += 1
                elif task.status == DownloadStatus.CANCELLED:
                    stats['cancelled'] += 1
            
            return stats


# 创建全局下载队列实例
download_queue = DownloadQueue(max_concurrent=2, auto_start=False)

