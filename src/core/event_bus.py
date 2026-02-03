"""
YouTube Downloader 事件总线模块
实现发布-订阅模式，用于解耦 UI 和业务逻辑
"""
import threading
import queue
from typing import Callable, Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import weakref

from src.utils.logger import LoggerManager


# ============ 事件名称常量 ============

class Events:
    """事件名称常量类"""
    
    # 下载相关事件
    DOWNLOAD_STARTED = "download:started"
    DOWNLOAD_PROGRESS = "download:progress"
    DOWNLOAD_COMPLETED = "download:completed"
    DOWNLOAD_FAILED = "download:failed"
    DOWNLOAD_CANCELLED = "download:cancelled"
    DOWNLOAD_PAUSED = "download:paused"
    DOWNLOAD_RESUMED = "download:resumed"
    
    # 队列相关事件
    QUEUE_TASK_ADDED = "queue:task_added"
    QUEUE_TASK_REMOVED = "queue:task_removed"
    QUEUE_STARTED = "queue:started"
    QUEUE_STOPPED = "queue:stopped"
    QUEUE_CLEARED = "queue:cleared"
    
    # 视频解析相关事件
    VIDEO_PARSE_STARTED = "video:parse_started"
    VIDEO_PARSE_COMPLETED = "video:parse_completed"
    VIDEO_PARSE_FAILED = "video:parse_failed"
    
    # Cookie 相关事件
    COOKIE_UPDATED = "cookie:updated"
    COOKIE_VALIDATED = "cookie:validated"
    COOKIE_EXPIRED = "cookie:expired"
    COOKIE_CLEARED = "cookie:cleared"
    
    # 版本相关事件
    VERSION_CHECK_STARTED = "version:check_started"
    VERSION_CHECK_COMPLETED = "version:check_completed"
    VERSION_UPDATE_STARTED = "version:update_started"
    VERSION_UPDATE_PROGRESS = "version:update_progress"
    VERSION_UPDATE_COMPLETED = "version:update_completed"
    VERSION_UPDATE_FAILED = "version:update_failed"
    
    # 应用相关事件
    APP_STARTED = "app:started"
    APP_CLOSING = "app:closing"
    APP_ERROR = "app:error"
    
    # 配置相关事件
    CONFIG_CHANGED = "config:changed"
    CONFIG_SAVED = "config:saved"
    CONFIG_LOADED = "config:loaded"
    
    # 通知相关事件
    NOTIFICATION_SHOW = "notification:show"
    NOTIFICATION_HIDE = "notification:hide"


# ============ 事件数据类 ============

@dataclass
class Event:
    """事件数据类"""
    name: str                              # 事件名称
    data: Dict[str, Any] = field(default_factory=dict)  # 事件数据
    timestamp: datetime = field(default_factory=datetime.now)  # 事件时间
    source: Optional[str] = None           # 事件来源
    
    def __str__(self) -> str:
        return f"Event({self.name}, data={self.data}, source={self.source})"


# ============ 订阅者包装器 ============

class SubscriberWrapper:
    """订阅者包装器，支持弱引用"""
    
    def __init__(self, callback: Callable, use_weak_ref: bool = False):
        self.use_weak_ref = use_weak_ref
        if use_weak_ref:
            # 对于方法，使用弱引用
            if hasattr(callback, '__self__'):
                self._weak_ref = weakref.WeakMethod(callback)
            else:
                self._weak_ref = weakref.ref(callback)
            self._callback = None
        else:
            self._callback = callback
            self._weak_ref = None
    
    def __call__(self, event: Event) -> bool:
        """调用回调函数，返回是否成功"""
        callback = self.get_callback()
        if callback is None:
            return False
        try:
            callback(event)
            return True
        except Exception:
            return False
    
    def get_callback(self) -> Optional[Callable]:
        """获取回调函数"""
        if self._callback:
            return self._callback
        if self._weak_ref:
            return self._weak_ref()
        return None
    
    def is_alive(self) -> bool:
        """检查回调是否仍然有效"""
        return self.get_callback() is not None


# ============ 事件总线 ============

class EventBus:
    """
    事件总线类
    实现单例模式的发布-订阅系统
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
        self._subscribers: Dict[str, List[SubscriberWrapper]] = {}
        self._lock = threading.RLock()
        self._event_queue: queue.Queue = queue.Queue()
        self._async_enabled = False
        self._async_thread: Optional[threading.Thread] = None
        self._running = False
        self.logger = LoggerManager().get_logger()
    
    def subscribe(
        self, 
        event_name: str, 
        callback: Callable[[Event], None],
        use_weak_ref: bool = False
    ) -> Callable[[], None]:
        """
        订阅事件
        
        Args:
            event_name: 事件名称
            callback: 回调函数，接收 Event 对象
            use_weak_ref: 是否使用弱引用（避免循环引用）
            
        Returns:
            取消订阅的函数
            
        Example:
            def on_download_progress(event):
                print(f"Progress: {event.data['progress']}%")
            
            unsubscribe = event_bus.subscribe(Events.DOWNLOAD_PROGRESS, on_download_progress)
            # 稍后取消订阅
            unsubscribe()
        """
        wrapper = SubscriberWrapper(callback, use_weak_ref)
        
        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(wrapper)
        
        self.logger.debug(f"订阅事件: {event_name}")
        
        # 返回取消订阅函数
        def unsubscribe():
            self._unsubscribe(event_name, wrapper)
        
        return unsubscribe
    
    def _unsubscribe(self, event_name: str, wrapper: SubscriberWrapper):
        """取消订阅"""
        with self._lock:
            if event_name in self._subscribers:
                try:
                    self._subscribers[event_name].remove(wrapper)
                    self.logger.debug(f"取消订阅事件: {event_name}")
                except ValueError:
                    pass
    
    def unsubscribe_all(self, event_name: str = None):
        """
        取消所有订阅
        
        Args:
            event_name: 事件名称，如果为 None 则取消所有事件的订阅
        """
        with self._lock:
            if event_name:
                self._subscribers.pop(event_name, None)
                self.logger.debug(f"取消事件所有订阅: {event_name}")
            else:
                self._subscribers.clear()
                self.logger.debug("取消所有事件订阅")
    
    def publish(
        self, 
        event_name: str, 
        data: Dict[str, Any] = None,
        source: str = None,
        async_mode: bool = False
    ):
        """
        发布事件
        
        Args:
            event_name: 事件名称
            data: 事件数据
            source: 事件来源
            async_mode: 是否异步发布
            
        Example:
            event_bus.publish(Events.DOWNLOAD_PROGRESS, {
                'progress': 50.0,
                'speed': '1.5 MiB/s',
                'eta': '02:30'
            })
        """
        event = Event(
            name=event_name,
            data=data or {},
            source=source
        )
        
        if async_mode and self._async_enabled:
            self._event_queue.put(event)
        else:
            self._dispatch(event)
    
    def _dispatch(self, event: Event):
        """分发事件给订阅者"""
        with self._lock:
            subscribers = self._subscribers.get(event.name, []).copy()
        
        # 清理无效的订阅者
        invalid_wrappers = []
        
        for wrapper in subscribers:
            if not wrapper.is_alive():
                invalid_wrappers.append(wrapper)
                continue
            
            try:
                wrapper(event)
            except Exception as e:
                self.logger.error(f"事件处理器错误 ({event.name}): {str(e)}")
        
        # 移除无效的订阅者
        if invalid_wrappers:
            with self._lock:
                for wrapper in invalid_wrappers:
                    if event.name in self._subscribers:
                        try:
                            self._subscribers[event.name].remove(wrapper)
                        except ValueError:
                            pass
    
    def emit(self, event_name: str, **kwargs):
        """
        发布事件的简便方法
        
        Args:
            event_name: 事件名称
            **kwargs: 事件数据
            
        Example:
            event_bus.emit(Events.DOWNLOAD_PROGRESS, progress=50.0, speed='1.5 MiB/s')
        """
        self.publish(event_name, data=kwargs)
    
    def on(self, event_name: str):
        """
        装饰器方式订阅事件
        
        Example:
            @event_bus.on(Events.DOWNLOAD_COMPLETED)
            def handle_download_completed(event):
                print(f"下载完成: {event.data['title']}")
        """
        def decorator(func: Callable[[Event], None]):
            self.subscribe(event_name, func)
            return func
        return decorator
    
    def once(self, event_name: str, callback: Callable[[Event], None]):
        """
        订阅一次性事件（触发后自动取消订阅）
        
        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        def wrapper(event: Event):
            try:
                callback(event)
            finally:
                self._unsubscribe(event_name, wrapper_holder[0])
        
        wrapper_holder = [None]
        subscriber = SubscriberWrapper(wrapper)
        wrapper_holder[0] = subscriber
        
        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(subscriber)
    
    def enable_async(self):
        """启用异步事件处理"""
        if self._async_enabled:
            return
        
        self._async_enabled = True
        self._running = True
        self._async_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._async_thread.start()
        self.logger.info("异步事件处理已启用")
    
    def disable_async(self):
        """禁用异步事件处理"""
        if not self._async_enabled:
            return
        
        self._running = False
        self._event_queue.put(None)  # 发送停止信号
        
        if self._async_thread:
            self._async_thread.join(timeout=2.0)
        
        self._async_enabled = False
        self.logger.info("异步事件处理已禁用")
    
    def _process_queue(self):
        """处理异步事件队列"""
        while self._running:
            try:
                event = self._event_queue.get(timeout=0.1)
                if event is None:  # 停止信号
                    break
                self._dispatch(event)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"异步事件处理错误: {str(e)}")
    
    def get_subscriber_count(self, event_name: str = None) -> int:
        """
        获取订阅者数量
        
        Args:
            event_name: 事件名称，如果为 None 则返回所有订阅者总数
        """
        with self._lock:
            if event_name:
                return len(self._subscribers.get(event_name, []))
            return sum(len(subs) for subs in self._subscribers.values())
    
    def get_subscribed_events(self) -> List[str]:
        """获取所有有订阅者的事件名称"""
        with self._lock:
            return [name for name, subs in self._subscribers.items() if subs]
    
    def clear(self):
        """清除所有订阅和事件队列"""
        with self._lock:
            self._subscribers.clear()
        
        # 清空队列
        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
            except queue.Empty:
                break
        
        self.logger.info("事件总线已清空")


# ============ 全局事件总线实例 ============

def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    return EventBus()


# 便捷访问
event_bus = EventBus()

