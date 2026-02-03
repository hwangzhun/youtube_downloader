"""
YouTube Downloader 类型定义模块
集中定义所有类型提示，包括 TypedDict、Protocol 和类型别名
"""
from typing import (
    TypedDict, Optional, List, Dict, Any, Callable, 
    Union, Protocol, Literal, Tuple
)
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime


# ============ 枚举类型 ============

class DownloadStatus(Enum):
    """下载状态枚举"""
    PENDING = auto()      # 等待中
    QUEUED = auto()       # 已加入队列
    DOWNLOADING = auto()  # 下载中
    PAUSED = auto()       # 已暂停
    COMPLETED = auto()    # 已完成
    FAILED = auto()       # 失败
    CANCELLED = auto()    # 已取消


class FormatType(Enum):
    """格式类型枚举"""
    VIDEO = "video"
    AUDIO = "audio"
    VIDEO_AUDIO = "video+audio"


class DownloadPriority(Enum):
    """下载优先级枚举"""
    HIGH = 1
    NORMAL = 2
    LOW = 3


class CookieStatus(Enum):
    """Cookie 状态枚举"""
    NOT_SET = auto()      # 未设置
    VALID = auto()        # 有效
    INVALID = auto()      # 无效
    EXPIRED = auto()      # 已过期


# ============ TypedDict 定义 ============

class ProgressInfo(TypedDict):
    """下载进度信息"""
    progress: float          # 进度百分比 (0-100)
    speed: str               # 下载速度 (如 "1.5 MiB/s")
    eta: str                 # 预计剩余时间 (如 "02:30")
    downloaded_bytes: int    # 已下载字节数
    total_bytes: int         # 总字节数
    filename: str            # 当前下载的文件名


class VideoInfo(TypedDict):
    """视频信息"""
    id: str                  # 视频 ID
    title: str               # 标题
    description: str         # 描述
    duration: int            # 时长（秒）
    uploader: str            # 上传者
    uploader_id: str         # 上传者 ID
    upload_date: str         # 上传日期
    view_count: int          # 观看次数
    like_count: int          # 点赞数
    thumbnail: str           # 缩略图 URL
    is_live: bool            # 是否为直播
    formats: List['FormatInfo']  # 可用格式列表


class FormatInfo(TypedDict):
    """视频格式信息"""
    format_id: str           # 格式 ID
    type: str                # 类型 (video/audio)
    resolution: str          # 分辨率 (如 "1920x1080")
    fps: int                 # 帧率
    vcodec: str              # 视频编码
    acodec: str              # 音频编码
    abr: float               # 音频比特率 (kbps)
    vbr: float               # 视频比特率 (kbps)
    asr: int                 # 音频采样率
    filesize: int            # 文件大小（字节）
    protocol: str            # 协议
    has_audio: bool          # 是否包含音频
    format_note: str         # 格式说明
    display: str             # 显示文本


class DownloadTask(TypedDict):
    """下载任务"""
    id: str                  # 任务 ID
    url: str                 # 视频 URL
    title: str               # 视频标题
    output_dir: str          # 输出目录
    video_format_id: str     # 视频格式 ID
    audio_format_id: str     # 音频格式 ID
    status: str              # 状态
    priority: int            # 优先级
    progress: float          # 进度
    speed: str               # 速度
    eta: str                 # 剩余时间
    error_message: str       # 错误信息
    created_at: str          # 创建时间
    started_at: str          # 开始时间
    completed_at: str        # 完成时间


class DownloadRecord(TypedDict):
    """下载历史记录"""
    id: str                  # 记录 ID
    url: str                 # 视频 URL
    title: str               # 视频标题
    file_path: str           # 文件路径
    format: str              # 格式
    size: int                # 文件大小
    duration: int            # 时长
    downloaded_at: str       # 下载时间
    status: str              # 状态


class CookieInfo(TypedDict):
    """Cookie 信息"""
    file_path: str           # Cookie 文件路径
    is_valid: bool           # 是否有效
    user_id: str             # 用户 ID
    username: str            # 用户名
    expires_at: str          # 过期时间


class VersionInfo(TypedDict):
    """版本信息"""
    component: str           # 组件名称 (yt-dlp/ffmpeg)
    current_version: str     # 当前版本
    latest_version: str      # 最新版本
    has_update: bool         # 是否有更新
    download_url: str        # 下载 URL


class AppConfig(TypedDict):
    """应用配置"""
    download_dir: str        # 下载目录
    use_cookies: bool        # 是否使用 Cookie
    auto_cookies: bool       # 是否自动获取 Cookie
    cookies_file: str        # Cookie 文件路径
    prefer_mp4: bool         # 是否优先 MP4
    default_format: str      # 默认格式
    show_notifications: bool # 是否显示通知
    check_updates: bool      # 是否检查更新
    max_concurrent: int      # 最大并发数
    auto_start_queue: bool   # 是否自动开始队列


# ============ Protocol 定义 ============

class ProgressCallback(Protocol):
    """进度回调协议"""
    def __call__(
        self, 
        progress: float, 
        speed: str, 
        eta: str, 
        title: str,
        video_index: int,
        total_videos: int
    ) -> None: ...


class CompletionCallback(Protocol):
    """完成回调协议"""
    def __call__(self, success: bool, output_path: str, error_message: str = None) -> None: ...


class ErrorCallback(Protocol):
    """错误回调协议"""
    def __call__(self, error_message: str) -> None: ...


class EventHandler(Protocol):
    """事件处理器协议"""
    def __call__(self, event_data: Any) -> None: ...


class CacheLoader(Protocol):
    """缓存加载器协议"""
    def load(self, key: str) -> Optional[Any]: ...
    def save(self, key: str, value: Any) -> bool: ...
    def delete(self, key: str) -> bool: ...
    def exists(self, key: str) -> bool: ...


# ============ 数据类 ============

@dataclass
class DownloadOptions:
    """下载选项"""
    url: str
    output_dir: str
    video_format_id: str = "best"
    audio_format_id: str = "best"
    use_cookies: bool = False
    cookies_file: Optional[str] = None
    prefer_mp4: bool = True
    no_playlist: bool = True
    priority: DownloadPriority = DownloadPriority.NORMAL
    # 代理设置
    proxy_url: Optional[str] = None


@dataclass
class ParsedUrl:
    """解析后的 URL 信息"""
    original_url: str
    video_id: str
    is_playlist: bool = False
    playlist_id: Optional[str] = None
    is_valid: bool = True
    error_message: Optional[str] = None


@dataclass
class DownloadResult:
    """下载结果"""
    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    duration: float = 0.0
    file_size: int = 0


@dataclass
class QueueItem:
    """队列项"""
    id: str
    task: DownloadTask
    priority: DownloadPriority = DownloadPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    
    def __lt__(self, other: 'QueueItem') -> bool:
        """用于优先级队列比较"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


# ============ 类型别名 ============

# URL 类型
Url = str

# 格式 ID
FormatId = str

# 文件路径
FilePath = str

# 进度值 (0-100)
Progress = float

# 字节大小
ByteSize = int

# 时间戳
Timestamp = float

# 版本号
Version = str

# 事件名称
EventName = str

# 事件数据
EventData = Dict[str, Any]

# 配置字典
ConfigDict = Dict[str, Any]

# 格式列表
FormatList = List[FormatInfo]

# 任务列表
TaskList = List[DownloadTask]

# 历史记录列表
HistoryList = List[DownloadRecord]

# 回调函数类型
ProgressCallbackType = Callable[[float, str, str, str, int, int], None]
CompletionCallbackType = Callable[[bool, str, Optional[str]], None]
ErrorCallbackType = Callable[[str], None]
UpdateProgressCallbackType = Callable[[int, str], None]

# 事件处理函数类型
EventHandlerType = Callable[[EventData], None]

