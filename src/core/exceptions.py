"""
YouTube Downloader 统一异常处理模块
定义所有自定义异常类，提供统一的错误处理机制
"""
from typing import Optional, Any
from functools import wraps


class YouTubeDownloaderError(Exception):
    """
    YouTube Downloader 基础异常类
    所有自定义异常都应继承此类
    """
    
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Any] = None):
        """
        初始化异常
        
        Args:
            message: 错误消息
            code: 错误代码（可选）
            details: 详细信息（可选）
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details
    
    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'code': self.code,
            'details': self.details
        }


# ============ 视频解析相关异常 ============

class VideoParseError(YouTubeDownloaderError):
    """视频解析错误"""
    
    def __init__(self, message: str = "视频解析失败", url: Optional[str] = None, **kwargs):
        super().__init__(message, code="VIDEO_PARSE_ERROR", **kwargs)
        self.url = url


class VideoUnavailableError(VideoParseError):
    """视频不可用错误"""
    
    def __init__(self, message: str = "视频不可用", **kwargs):
        super().__init__(message, **kwargs)
        self.code = "VIDEO_UNAVAILABLE"


class VideoPrivateError(VideoParseError):
    """私人视频错误"""
    
    def __init__(self, message: str = "这是私人视频，需要登录才能访问", **kwargs):
        super().__init__(message, **kwargs)
        self.code = "VIDEO_PRIVATE"


class VideoAgeRestrictedError(VideoParseError):
    """年龄限制视频错误"""
    
    def __init__(self, message: str = "此视频有年龄限制，请设置 Cookie 后重试", **kwargs):
        super().__init__(message, **kwargs)
        self.code = "VIDEO_AGE_RESTRICTED"


class VideoLiveError(VideoParseError):
    """直播视频错误"""
    
    def __init__(self, message: str = "无法下载正在进行的直播", **kwargs):
        super().__init__(message, **kwargs)
        self.code = "VIDEO_LIVE"


class InvalidUrlError(VideoParseError):
    """无效 URL 错误"""
    
    def __init__(self, message: str = "无效的视频链接", **kwargs):
        super().__init__(message, **kwargs)
        self.code = "INVALID_URL"


# ============ 下载相关异常 ============

class DownloadError(YouTubeDownloaderError):
    """下载错误基类"""
    
    def __init__(self, message: str = "下载失败", url: Optional[str] = None, **kwargs):
        super().__init__(message, code="DOWNLOAD_ERROR", **kwargs)
        self.url = url


class DownloadCancelledError(DownloadError):
    """下载取消错误"""
    
    def __init__(self, message: str = "下载已取消", **kwargs):
        super().__init__(message, **kwargs)
        self.code = "DOWNLOAD_CANCELLED"


class DownloadTimeoutError(DownloadError):
    """下载超时错误"""
    
    def __init__(self, message: str = "下载超时", **kwargs):
        super().__init__(message, **kwargs)
        self.code = "DOWNLOAD_TIMEOUT"


class InsufficientSpaceError(DownloadError):
    """磁盘空间不足错误"""
    
    def __init__(self, message: str = "磁盘空间不足", required: Optional[int] = None, 
                 available: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.code = "INSUFFICIENT_SPACE"
        self.required = required
        self.available = available


class FormatNotFoundError(DownloadError):
    """格式不存在错误"""
    
    def __init__(self, message: str = "请求的视频格式不存在", format_id: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.code = "FORMAT_NOT_FOUND"
        self.format_id = format_id


# ============ 网络相关异常 ============

class NetworkError(YouTubeDownloaderError):
    """网络错误基类"""
    
    def __init__(self, message: str = "网络错误", **kwargs):
        super().__init__(message, code="NETWORK_ERROR", **kwargs)


class ConnectionError(NetworkError):
    """连接错误"""
    
    def __init__(self, message: str = "无法连接到服务器", **kwargs):
        super().__init__(message, **kwargs)
        self.code = "CONNECTION_ERROR"


class RateLimitError(NetworkError):
    """请求频率限制错误"""
    
    def __init__(self, message: str = "请求过于频繁，请稍后再试", retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.code = "RATE_LIMIT"
        self.retry_after = retry_after


class ProxyError(NetworkError):
    """代理错误"""
    
    def __init__(self, message: str = "代理连接失败", **kwargs):
        super().__init__(message, **kwargs)
        self.code = "PROXY_ERROR"


# ============ Cookie 相关异常 ============

class CookieError(YouTubeDownloaderError):
    """Cookie 错误基类"""
    
    def __init__(self, message: str = "Cookie 错误", **kwargs):
        super().__init__(message, code="COOKIE_ERROR", **kwargs)


class CookieNotFoundError(CookieError):
    """Cookie 文件不存在错误"""
    
    def __init__(self, message: str = "Cookie 文件不存在", path: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.code = "COOKIE_NOT_FOUND"
        self.path = path


class CookieInvalidError(CookieError):
    """Cookie 无效错误"""
    
    def __init__(self, message: str = "Cookie 无效或已过期", **kwargs):
        super().__init__(message, **kwargs)
        self.code = "COOKIE_INVALID"


class CookieExtractionError(CookieError):
    """Cookie 提取错误"""
    
    def __init__(self, message: str = "无法从浏览器提取 Cookie", browser: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.code = "COOKIE_EXTRACTION_ERROR"
        self.browser = browser


# ============ 二进制文件相关异常 ============

class BinaryError(YouTubeDownloaderError):
    """二进制文件错误基类"""
    
    def __init__(self, message: str = "二进制文件错误", binary_name: Optional[str] = None, **kwargs):
        super().__init__(message, code="BINARY_ERROR", **kwargs)
        self.binary_name = binary_name


class BinaryNotFoundError(BinaryError):
    """二进制文件不存在错误"""
    
    def __init__(self, message: str = "二进制文件不存在", **kwargs):
        super().__init__(message, **kwargs)
        self.code = "BINARY_NOT_FOUND"


class BinaryUpdateError(BinaryError):
    """二进制文件更新错误"""
    
    def __init__(self, message: str = "更新失败", **kwargs):
        super().__init__(message, **kwargs)
        self.code = "BINARY_UPDATE_ERROR"


# ============ 配置相关异常 ============

class ConfigError(YouTubeDownloaderError):
    """配置错误基类"""
    
    def __init__(self, message: str = "配置错误", **kwargs):
        super().__init__(message, code="CONFIG_ERROR", **kwargs)


class ConfigLoadError(ConfigError):
    """配置加载错误"""
    
    def __init__(self, message: str = "无法加载配置文件", path: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.code = "CONFIG_LOAD_ERROR"
        self.path = path


class ConfigSaveError(ConfigError):
    """配置保存错误"""
    
    def __init__(self, message: str = "无法保存配置文件", **kwargs):
        super().__init__(message, **kwargs)
        self.code = "CONFIG_SAVE_ERROR"


# ============ 异常处理装饰器 ============

def handle_errors(error_type: type = YouTubeDownloaderError, 
                  message: str = "操作失败",
                  reraise: bool = True):
    """
    异常处理装饰器
    
    Args:
        error_type: 要抛出的异常类型
        message: 错误消息
        reraise: 是否重新抛出异常
        
    Example:
        @handle_errors(VideoParseError, "视频解析失败")
        def parse_video(url):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except error_type:
                # 如果已经是预期的异常类型，直接重新抛出
                raise
            except Exception as e:
                # 将其他异常包装为指定类型
                new_error = error_type(f"{message}: {str(e)}", details=str(e))
                if reraise:
                    raise new_error from e
                return None
        return wrapper
    return decorator


def safe_execute(default=None, log_error: bool = True):
    """
    安全执行装饰器，捕获所有异常并返回默认值
    
    Args:
        default: 发生异常时返回的默认值
        log_error: 是否记录错误日志
        
    Example:
        @safe_execute(default=[])
        def get_formats():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    from src.utils.logger import LoggerManager
                    logger = LoggerManager().get_logger()
                    logger.error(f"执行 {func.__name__} 时发生错误: {str(e)}", exc_info=True)
                return default
        return wrapper
    return decorator


# ============ 异常映射工具 ============

class ExceptionMapper:
    """异常映射器，将原始错误消息映射为用户友好的异常"""
    
    # 错误消息到异常类的映射
    ERROR_PATTERNS = {
        'Video unavailable': VideoUnavailableError,
        'This video is unavailable': VideoUnavailableError,
        'This video is private': VideoPrivateError,
        'Sign in to confirm your age': VideoAgeRestrictedError,
        'Video is age restricted': VideoAgeRestrictedError,
        'This live event will begin': VideoLiveError,
        'Premieres in': VideoLiveError,
        'HTTP Error 429': RateLimitError,
        'Too Many Requests': RateLimitError,
        'Connection reset': ConnectionError,
        'Unable to extract': VideoParseError,
        'No video formats found': FormatNotFoundError,
    }
    
    @classmethod
    def map_error(cls, error_message: str, url: Optional[str] = None) -> YouTubeDownloaderError:
        """
        根据错误消息映射到对应的异常类
        
        Args:
            error_message: 原始错误消息
            url: 相关的 URL（可选）
            
        Returns:
            对应的异常实例
        """
        error_message_lower = error_message.lower()
        
        for pattern, exception_class in cls.ERROR_PATTERNS.items():
            if pattern.lower() in error_message_lower:
                return exception_class(details=error_message, url=url)
        
        # 默认返回基础下载错误
        return DownloadError(f"下载出错: {error_message}", url=url)

