"""
YouTube Downloader 服务定位器模块
统一管理核心服务实例，实现依赖注入
"""
import threading
from typing import Dict, Any, Optional, Type, TypeVar, Callable
from functools import wraps

from src.utils.logger import LoggerManager

T = TypeVar('T')


class ServiceLocator:
    """
    服务定位器类
    提供服务的注册、获取和生命周期管理
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
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._singletons: Dict[str, bool] = {}
        self._lock = threading.RLock()
        self.logger = LoggerManager().get_logger()
    
    def register(
        self, 
        name: str, 
        instance: Any = None,
        factory: Callable[[], Any] = None,
        singleton: bool = True
    ):
        """
        注册服务
        
        Args:
            name: 服务名称
            instance: 服务实例（与 factory 二选一）
            factory: 服务工厂函数（与 instance 二选一）
            singleton: 是否为单例（仅在使用 factory 时有效）
            
        Example:
            # 注册实例
            locator.register('downloader', VideoDownloader())
            
            # 注册工厂
            locator.register('cache', factory=lambda: VideoInfoCache(), singleton=True)
        """
        with self._lock:
            if instance is not None:
                self._services[name] = instance
                self._singletons[name] = True
                self.logger.debug(f"注册服务实例: {name}")
            elif factory is not None:
                self._factories[name] = factory
                self._singletons[name] = singleton
                self.logger.debug(f"注册服务工厂: {name} (singleton={singleton})")
            else:
                raise ValueError("必须提供 instance 或 factory")
    
    def register_class(
        self, 
        name: str, 
        cls: Type[T],
        singleton: bool = True,
        *args,
        **kwargs
    ):
        """
        注册类作为服务
        
        Args:
            name: 服务名称
            cls: 服务类
            singleton: 是否为单例
            *args, **kwargs: 传递给类构造函数的参数
            
        Example:
            locator.register_class('downloader', VideoDownloader)
        """
        def factory():
            return cls(*args, **kwargs)
        
        self.register(name, factory=factory, singleton=singleton)
    
    def get(self, name: str, default: Any = None) -> Optional[Any]:
        """
        获取服务
        
        Args:
            name: 服务名称
            default: 默认值（如果服务不存在）
            
        Returns:
            服务实例
            
        Example:
            downloader = locator.get('downloader')
        """
        with self._lock:
            # 首先检查是否已有实例
            if name in self._services:
                return self._services[name]
            
            # 检查是否有工厂
            if name in self._factories:
                instance = self._factories[name]()
                
                # 如果是单例，缓存实例
                if self._singletons.get(name, True):
                    self._services[name] = instance
                
                return instance
            
            return default
    
    def get_required(self, name: str) -> Any:
        """
        获取必需的服务（不存在时抛出异常）
        
        Args:
            name: 服务名称
            
        Returns:
            服务实例
            
        Raises:
            KeyError: 如果服务不存在
        """
        service = self.get(name)
        if service is None:
            raise KeyError(f"服务未注册: {name}")
        return service
    
    def has(self, name: str) -> bool:
        """检查服务是否已注册"""
        with self._lock:
            return name in self._services or name in self._factories
    
    def unregister(self, name: str):
        """
        注销服务
        
        Args:
            name: 服务名称
        """
        with self._lock:
            self._services.pop(name, None)
            self._factories.pop(name, None)
            self._singletons.pop(name, None)
            self.logger.debug(f"注销服务: {name}")
    
    def clear(self):
        """清除所有服务"""
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()
            self.logger.debug("清除所有服务")
    
    def get_all_names(self) -> list:
        """获取所有已注册的服务名称"""
        with self._lock:
            names = set(self._services.keys())
            names.update(self._factories.keys())
            return list(names)


# ============ 服务名称常量 ============

class Services:
    """服务名称常量"""
    
    # 核心服务
    DOWNLOADER = "downloader"
    VIDEO_INFO_PARSER = "video_info_parser"
    FORMAT_PARSER = "format_parser"
    COOKIE_MANAGER = "cookie_manager"
    VERSION_MANAGER = "version_manager"
    
    # 缓存服务
    VIDEO_CACHE = "video_cache"
    FORMAT_CACHE = "format_cache"
    
    # 管理服务
    CONFIG_MANAGER = "config_manager"
    DOWNLOAD_QUEUE = "download_queue"
    DOWNLOAD_HISTORY = "download_history"
    
    # 事件服务
    EVENT_BUS = "event_bus"
    
    # 通知服务
    NOTIFICATION_MANAGER = "notification_manager"


# ============ 依赖注入装饰器 ============

def inject(*service_names: str):
    """
    依赖注入装饰器
    
    自动从服务定位器获取服务并注入到函数参数
    
    Example:
        @inject(Services.DOWNLOADER, Services.CONFIG_MANAGER)
        def download_video(url, downloader, config_manager):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            locator = ServiceLocator()
            
            # 获取服务并添加到 kwargs
            for name in service_names:
                if name not in kwargs:
                    service = locator.get(name)
                    if service is not None:
                        # 使用服务名的最后一部分作为参数名
                        param_name = name.split('.')[-1] if '.' in name else name
                        kwargs[param_name] = service
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def injectable(service_name: str, singleton: bool = True):
    """
    可注入装饰器
    
    将类自动注册为服务
    
    Example:
        @injectable(Services.DOWNLOADER)
        class VideoDownloader:
            ...
    """
    def decorator(cls: Type[T]) -> Type[T]:
        ServiceLocator().register_class(service_name, cls, singleton=singleton)
        return cls
    return decorator


# ============ 服务初始化 ============

def init_services():
    """
    初始化所有核心服务
    
    应该在应用启动时调用
    """
    locator = ServiceLocator()
    
    # 导入并注册事件总线
    from src.core.event_bus import EventBus
    locator.register(Services.EVENT_BUS, EventBus())
    
    # 注册配置管理器
    from src.utils.config import ConfigManager
    locator.register(Services.CONFIG_MANAGER, ConfigManager())
    
    # 注册 Cookie 管理器
    from src.core.cookie_manager import CookieManager
    locator.register(Services.COOKIE_MANAGER, CookieManager())
    
    # 注册版本管理器
    from src.core.version_manager import VersionManager
    locator.register(Services.VERSION_MANAGER, VersionManager())
    
    # 注册下载器
    from src.core.downloader import VideoDownloader
    locator.register(Services.DOWNLOADER, VideoDownloader())
    
    # 注册视频信息解析器
    from src.core.video_info.video_info_parser import VideoInfoParser
    locator.register(Services.VIDEO_INFO_PARSER, VideoInfoParser())
    
    # 注册格式解析器
    from src.core.video_info.format_parser import FormatParser
    locator.register(Services.FORMAT_PARSER, FormatParser())
    
    # 注册通知管理器
    from src.utils.notification import NotificationManager
    locator.register(Services.NOTIFICATION_MANAGER, NotificationManager())
    
    LoggerManager().get_logger().info("所有核心服务已初始化")


def get_service(name: str) -> Any:
    """
    获取服务的便捷函数
    
    Args:
        name: 服务名称
        
    Returns:
        服务实例
    """
    return ServiceLocator().get(name)


# ============ 全局服务定位器实例 ============

service_locator = ServiceLocator()

