"""
YouTube Downloader 跨平台工具模块
负责处理跨平台兼容性和统一的子进程调用
"""
import os
import sys
import subprocess
from typing import List, Optional, Dict, Any, Union
from pathlib import Path

# Windows 特定常量：创建无窗口的子进程
CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0

# 平台标识
IS_WINDOWS = os.name == 'nt'
IS_MACOS = sys.platform == 'darwin'
IS_LINUX = sys.platform.startswith('linux')


def get_app_data_dir() -> Path:
    """
    获取应用程序数据目录
    
    Returns:
        应用数据目录路径
    """
    if IS_WINDOWS:
        base_dir = os.environ.get('APPDATA', '')
        return Path(base_dir) / 'YouTubeDownloader'
    elif IS_MACOS:
        return Path.home() / 'Library' / 'Application Support' / 'YouTubeDownloader'
    else:
        return Path.home() / '.youtube_downloader'


def get_logs_dir() -> Path:
    """
    获取日志目录
    
    Returns:
        日志目录路径
    """
    logs_dir = get_app_data_dir() / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_cache_dir() -> Path:
    """
    获取缓存目录
    
    Returns:
        缓存目录路径
    """
    cache_dir = get_app_data_dir() / 'cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_config_dir() -> Path:
    """
    获取配置目录
    
    Returns:
        配置目录路径
    """
    config_dir = get_app_data_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_project_root() -> Path:
    """
    获取项目根目录
    
    Returns:
        项目根目录路径
    """
    # 从当前文件向上查找项目根目录
    current = Path(__file__).resolve()
    # src/utils/platform.py -> 向上三级到项目根目录
    return current.parent.parent.parent


def get_binaries_dir() -> Path:
    """
    获取二进制文件目录
    
    Returns:
        二进制文件目录路径
    """
    return get_project_root() / 'resources' / 'binaries'


def get_yt_dlp_path() -> Path:
    """
    获取 yt-dlp 可执行文件路径
    
    Returns:
        yt-dlp 路径
    """
    exe_name = 'yt-dlp.exe' if IS_WINDOWS else 'yt-dlp'
    return get_binaries_dir() / 'yt-dlp' / exe_name


def get_ffmpeg_path() -> Path:
    """
    获取 ffmpeg 可执行文件路径
    
    Returns:
        ffmpeg 路径
    """
    exe_name = 'ffmpeg.exe' if IS_WINDOWS else 'ffmpeg'
    return get_binaries_dir() / 'ffmpeg' / exe_name


def get_ffprobe_path() -> Path:
    """
    获取 ffprobe 可执行文件路径
    
    Returns:
        ffprobe 路径
    """
    exe_name = 'ffprobe.exe' if IS_WINDOWS else 'ffprobe'
    return get_binaries_dir() / 'ffmpeg' / exe_name


def find_javascript_runtime() -> Optional[str]:
    """
    检测系统中可用的 JavaScript 运行时
    
    优先顺序：
    1. Node.js (node)
    2. Deno (deno)
    
    Returns:
        JavaScript 运行时名称（如 'node' 或 'deno'），如果未找到则返回 None
    """
    # 尝试检测 Node.js
    try:
        result = run_subprocess(
            ['node', '--version'],
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0
        )
        if result.returncode == 0:
            return 'node'
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    
    # 尝试检测 Deno
    try:
        result = run_subprocess(
            ['deno', '--version'],
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0
        )
        if result.returncode == 0:
            return 'deno'
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    
    return None


def get_js_runtime_args() -> List[str]:
    """
    获取 yt-dlp 的 JavaScript 运行时参数
    
    Returns:
        参数列表，如果找到运行时则返回 ['--js-runtimes', 'runtime']，否则返回空列表
    """
    runtime = find_javascript_runtime()
    if runtime:
        return ['--js-runtimes', runtime]
    return []


def run_subprocess(
    cmd: List[str],
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
    timeout: Optional[float] = None,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[Dict[str, str]] = None,
    **kwargs: Any
) -> subprocess.CompletedProcess:
    """
    跨平台安全执行子进程
    
    在 Windows 上自动添加 CREATE_NO_WINDOW 标志以避免弹出控制台窗口
    
    Args:
        cmd: 命令及参数列表
        capture_output: 是否捕获输出
        text: 是否以文本模式返回
        check: 是否在返回码非零时抛出异常
        timeout: 超时时间（秒）
        cwd: 工作目录
        env: 环境变量
        **kwargs: 其他传递给 subprocess.run 的参数
        
    Returns:
        subprocess.CompletedProcess 对象
        
    Raises:
        subprocess.CalledProcessError: 当 check=True 且返回码非零时
        subprocess.TimeoutExpired: 当超时时
    """
    # 设置默认参数
    default_kwargs = {
        'capture_output': capture_output,
        'text': text,
        'check': check,
        'timeout': timeout,
        'cwd': cwd,
        'env': env,
    }
    
    # Windows 特定：添加 CREATE_NO_WINDOW 标志
    if IS_WINDOWS:
        default_kwargs['creationflags'] = CREATE_NO_WINDOW
    
    # 合并用户提供的参数
    default_kwargs.update(kwargs)
    
    # 移除 None 值
    default_kwargs = {k: v for k, v in default_kwargs.items() if v is not None}
    
    return subprocess.run(cmd, **default_kwargs)


def run_subprocess_with_output(
    cmd: List[str],
    timeout: Optional[float] = None,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[Dict[str, str]] = None,
) -> tuple:
    """
    执行子进程并返回输出和返回码
    
    Args:
        cmd: 命令及参数列表
        timeout: 超时时间（秒）
        cwd: 工作目录
        env: 环境变量
        
    Returns:
        (stdout, stderr, return_code) 元组
    """
    try:
        result = run_subprocess(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            cwd=cwd,
            env=env
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return '', 'Process timed out', -1
    except Exception as e:
        return '', str(e), -1


def create_popen(
    cmd: List[str],
    stdout: Any = subprocess.PIPE,
    stderr: Any = subprocess.STDOUT,
    text: bool = True,
    bufsize: int = 1,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[Dict[str, str]] = None,
    **kwargs: Any
) -> subprocess.Popen:
    """
    创建跨平台的 Popen 对象，用于需要实时读取输出的场景
    
    Args:
        cmd: 命令及参数列表
        stdout: stdout 处理方式
        stderr: stderr 处理方式
        text: 是否以文本模式
        bufsize: 缓冲区大小
        cwd: 工作目录
        env: 环境变量
        **kwargs: 其他传递给 Popen 的参数
        
    Returns:
        subprocess.Popen 对象
    """
    popen_kwargs = {
        'stdout': stdout,
        'stderr': stderr,
        'text': text,
        'bufsize': bufsize,
        'universal_newlines': text,
    }
    
    if cwd:
        popen_kwargs['cwd'] = cwd
    if env:
        popen_kwargs['env'] = env
    
    # Windows 特定：添加 CREATE_NO_WINDOW 标志
    if IS_WINDOWS:
        popen_kwargs['creationflags'] = CREATE_NO_WINDOW
    
    popen_kwargs.update(kwargs)
    
    return subprocess.Popen(cmd, **popen_kwargs)


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        path: 目录路径
        
    Returns:
        Path 对象
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_path_join(*parts: Union[str, Path]) -> Path:
    """
    安全地拼接路径
    
    Args:
        *parts: 路径部分
        
    Returns:
        拼接后的 Path 对象
    """
    return Path(*parts)

