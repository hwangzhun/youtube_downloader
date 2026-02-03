"""
YouTube DownLoader 视频下载核心模块
负责处理视频下载相关的核心功能，支持同步和异步下载
"""
import os
import re
import json
import threading
import time
import uuid
from typing import List, Dict, Tuple, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

from src.utils.logger import LoggerManager
from src.utils.platform import (
    run_subprocess, create_popen, get_yt_dlp_path, get_ffmpeg_path, get_js_runtime_args
)
from src.core.event_bus import event_bus, Events
from src.core.exceptions import DownloadError, DownloadCancelledError
from src.types import DownloadStatus, DownloadOptions, DownloadResult

class VideoDownloader:
    """YouTube DownLoader 视频下载器类"""
    
    def __init__(self, yt_dlp_path: str = None, ffmpeg_path: str = None):
        """
        初始化下载器
        
        Args:
            yt_dlp_path: yt-dlp 可執行文件路径，如果为 None 則使用內置路径
            ffmpeg_path: ffmpeg 可執行文件路径，如果为 None 則使用內置路径
        """
        # 初始化日志
        self.logger = LoggerManager().get_logger()
        
        # 获取当前脚本所在目录
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 设置 yt-dlp 和 ffmpeg 路径
        self.yt_dlp_path = yt_dlp_path or str(get_yt_dlp_path())
        self.ffmpeg_path = ffmpeg_path or str(get_ffmpeg_path())
        
        # 记录初始化信息
        self.logger.info(f"初始化下载器 - yt-dlp路径: {self.yt_dlp_path}, ffmpeg路径: {self.ffmpeg_path}")
        
        # 下載狀態
        self.is_downloading = False
        self.current_progress = 0
        self.download_speed = "0 KiB/s"
        self.eta = "00:00"
        self.current_video_title = ""
        self.current_video_index = 0
        self.total_videos = 0
        self.start_time = 0
        self.current_url = ""
        
        # 錯誤信息收集
        self.current_error_lines = []
        
        # 下載進程
        self.download_process = None
        self.download_thread = None
        
        # 回調函數
        self.progress_callback = None
        self.completion_callback = None
        self.error_callback = None
    
    def set_callbacks(self, 
                     progress_callback: Callable[[float, str, str, str, int, int], None] = None,
                     completion_callback: Callable[[bool, str], None] = None,
                     error_callback: Callable[[str], None] = None):
        """
        設置回調函數
        
        Args:
            progress_callback: 進度回調函數，參數为(進度百分比, 下載速度, 剩餘時間, 當前视频标题, 當前视频索引, 總视频數)
            completion_callback: 完成回調函數，參數为(是否成功, 輸出目錄)
            error_callback: 錯誤回調函數，參數为(錯誤信息)
        """
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.error_callback = error_callback
    
    def extract_video_info(self, url: str, use_cookies: bool = False, cookies_file: str = None, proxy_url: str = None) -> Dict:
        """
        提取视频信息
        
        Args:
            url: 视频URL
            use_cookies: 是否使用cookies
            cookies_file: cookies文件路径
            proxy_url: 代理URL
            
        Returns:
            视频信息字典
        """
        self.logger.info(f"开始提取视频信息 - URL: {url}, 使用Cookie: {use_cookies}, 使用代理: {bool(proxy_url)}")
        
        cmd = [self.yt_dlp_path, '--dump-json', '--no-playlist', url]
        
        # 添加 JavaScript 运行时支持
        js_runtime_args = get_js_runtime_args()
        if js_runtime_args:
            cmd.extend(js_runtime_args)
            self.logger.info(f"使用JavaScript运行时: {js_runtime_args[1]}")
        
        if use_cookies and cookies_file:
            cmd.extend(['--cookies', cookies_file])
            self.logger.info(f"使用Cookie文件: {cookies_file}")
        
        if proxy_url:
            cmd.extend(['--proxy', proxy_url])
            self.logger.info(f"使用代理: {proxy_url}")
        
        try:
            result = run_subprocess(cmd, check=True)
            video_info = json.loads(result.stdout)
            self.logger.info(f"成功提取视频信息 - 标题: {video_info.get('title', '未知')}")
            return video_info
        except Exception as e:
            error_msg = f"提取视频信息失败: {e.stderr}"
            self.logger.error(error_msg)
            if self.error_callback:
                self.error_callback(error_msg)
            return {}
        except json.JSONDecodeError:
            error_msg = "解析视频信息失败"
            self.logger.error(error_msg)
            if self.error_callback:
                self.error_callback(error_msg)
            return {}
    
    def get_available_formats(self, url: str, use_cookies: bool = False, cookies_file: str = None, proxy_url: str = None) -> List[Dict]:
        """
        获取可用的视频格式
        
        Args:
            url: 视频URL
            use_cookies: 是否使用cookies
            cookies_file: cookies文件路径
            proxy_url: 代理URL
            
        Returns:
            格式列表，每個格式为一個字典
        """
        self.logger.info(f"开始获取可用格式 - URL: {url}")
        
        video_info = self.extract_video_info(url, use_cookies, cookies_file, proxy_url)
        if not video_info:
            self.logger.warning("无法获取视频信息，无法获取可用格式")
            return []
        
        formats = video_info.get('formats', [])
        # 過濾並整理格式信息
        result = []
        for fmt in formats:
            if 'height' in fmt and fmt.get('height'):
                result.append({
                    'format_id': fmt.get('format_id', ''),
                    'ext': fmt.get('ext', ''),
                    'resolution': f"{fmt.get('width', '?')}x{fmt.get('height', '?')}",
                    'fps': fmt.get('fps', ''),
                    'filesize': fmt.get('filesize', 0),
                    'format_note': fmt.get('format_note', ''),
                    'vcodec': fmt.get('vcodec', ''),
                    'acodec': fmt.get('acodec', '')
                })
        
        # 按分辨率排序（從高到低）
        result.sort(key=lambda x: int(x['resolution'].split('x')[1]) if 'x' in x['resolution'] and x['resolution'].split('x')[1].isdigit() else 0, reverse=True)
        
        self.logger.info(f"成功获取可用格式 - 共 {len(result)} 种格式")
        return result
    
    def parse_progress(self, line: str) -> None:
        """
        解析进度输出
        
        Args:
            line: yt-dlp 輸出的一行
        """
        # 檢測錯誤行（以 ERROR: 開頭）
        if line.strip().startswith('ERROR:'):
            error_text = line.strip()
            if error_text not in self.current_error_lines:
                self.current_error_lines.append(error_text)
                self.logger.error(f"檢測到錯誤: {error_text}")
            # 錯誤行不進行進度解析，直接返回
            return
        
        # 解析進度百分比
        progress_match = re.search(r'(\d+\.\d+)%', line)
        if progress_match:
            self.current_progress = float(progress_match.group(1))
        
        # 解析下載速度
        speed_match = re.search(r'(\d+\.\d+\s*[KMG]iB/s)', line)
        if speed_match:
            self.download_speed = speed_match.group(1)
        
        # 解析剩餘時間
        eta_match = re.search(r'ETA\s+(\d+:\d+)', line)
        if eta_match:
            self.eta = eta_match.group(1)
        
        # 解析當前视频标题
        title_match = re.search(r'\[download\]\s+Destination:\s+(.+)', line)
        if title_match:
            self.current_video_title = os.path.basename(title_match.group(1))
        
        # 記錄下載進度
        self.logger.info(f"下载进度 - URL: {self.current_url}, 进度: {self.current_progress:.2f}%, 速度: {self.download_speed}, ETA: {self.eta}")
        
        # 更新進度
        if self.progress_callback:
            self.progress_callback(
                self.current_progress,
                self.download_speed,
                self.eta,
                self.current_video_title,
                self.current_video_index,
                self.total_videos
            )
    
    def download_videos(self, 
                       urls: List[str], 
                       output_dir: str, 
                       format_id: str = 'best', 
                       use_cookies: bool = False, 
                       cookies_file: str = None,
                       prefer_mp4: bool = True,
                       no_playlist: bool = False,
                       proxy_url: str = None) -> None:
        """
        下載视频
        
        Args:
            urls: 视频URL列表
            output_dir: 輸出目錄
            format_id: 格式ID
            use_cookies: 是否使用cookies
            cookies_file: cookies文件路径
            prefer_mp4: 是否優先選擇MP4格式
            no_playlist: 是否禁止下载播放列表
            proxy_url: 代理URL
        """
        if self.is_downloading:
            error_msg = "已有下載任務正在進行"
            self.logger.warning(error_msg)
            if self.error_callback:
                self.error_callback(error_msg)
            return
        
        self.logger.info(f"开始下載任務 - URL數量: {len(urls)}, 格式: {format_id}, 使用Cookie: {use_cookies}, 優先MP4: {prefer_mp4}, 使用代理: {bool(proxy_url)}")
        
        self.is_downloading = True
        self.current_progress = 0
        self.download_speed = "0 KiB/s"
        self.eta = "00:00"
        self.current_video_title = ""
        self.current_video_index = 0
        self.total_videos = len(urls)
        self.start_time = time.time()
        self.current_error_lines = []  # 重置錯誤信息
        
        # 創建下載線程
        self.download_thread = threading.Thread(
            target=self._download_thread,
            args=(urls, output_dir, format_id, use_cookies, cookies_file, prefer_mp4, no_playlist, proxy_url)
        )
        self.download_thread.daemon = True
        self.download_thread.start()
    
    def _download_thread(self, 
                        urls: List[str], 
                        output_dir: str, 
                        format_id: str, 
                        use_cookies: bool, 
                        cookies_file: str,
                        prefer_mp4: bool,
                        no_playlist: bool,
                        proxy_url: str = None) -> None:
        """
        下載線程
        
        Args:
            urls: 视频URL列表
            output_dir: 輸出目錄
            format_id: 格式ID
            use_cookies: 是否使用cookies
            cookies_file: cookies文件路径
            prefer_mp4: 是否優先選擇MP4格式
            no_playlist: 是否禁止下载播放列表
            proxy_url: 代理URL
        """
        success = True
        error_message = ""
        
        try:
            # 確保輸出目錄存在
            os.makedirs(output_dir, exist_ok=True)
            self.logger.info(f"創建輸出目錄: {output_dir}")
            
            # 處理每個URL
            for i, url in enumerate(urls):
                if not self.is_downloading:
                    break
                
                self.current_video_index = i + 1
                self.current_url = url
                self.logger.info(f"开始下載第 {i+1}/{len(urls)} 個视频: {url}")
                
                # 如果格式ID不是"best"，先验证格式是否可用
                if format_id != "best":
                    try:
                        video_info = self.extract_video_info(url, use_cookies, cookies_file, proxy_url)
                        if video_info:
                            available_format_ids = [fmt.get('format_id', '') for fmt in video_info.get('formats', [])]
                            
                            # 检查格式ID（支持组合格式如 "313+251"）
                            if "+" in format_id:
                                # 组合格式：检查视频和音频格式是否都可用
                                video_fmt, audio_fmt = format_id.split("+", 1)
                                if video_fmt not in available_format_ids or audio_fmt not in available_format_ids:
                                    self.logger.warning(f"组合格式 {format_id} 不可用（视频: {video_fmt}, 音频: {audio_fmt}），回退到 best")
                                    format_id = "best"
                            else:
                                # 单个格式ID
                                if format_id not in available_format_ids:
                                    self.logger.warning(f"格式 {format_id} 不可用，回退到 best")
                                    format_id = "best"
                    except Exception as e:
                        self.logger.warning(f"验证格式时出错: {str(e)}，使用原始格式ID")
                
                # 構建命令
                cmd = [
                    self.yt_dlp_path,
                    '-f', format_id,
                    '-o', os.path.join(output_dir, '%(title)s.%(ext)s'),
                    '--newline',
                ]
                
                # 如果是单视频下载，添加 --no-playlist
                if no_playlist:
                    cmd.append('--no-playlist')
                
                # 添加 JavaScript 运行时支持
                js_runtime_args = get_js_runtime_args()
                if js_runtime_args:
                    cmd.extend(js_runtime_args)
                
                # 添加 ffmpeg 位置
                cmd.extend(['--ffmpeg-location', self.ffmpeg_path])
                
                # 如果優先選擇MP4格式
                if prefer_mp4:
                    cmd.extend(['--merge-output-format', 'mp4'])
                
                # 如果使用cookies
                if use_cookies and cookies_file:
                    cmd.extend(['--cookies', cookies_file])
                
                # 如果使用代理
                if proxy_url:
                    cmd.extend(['--proxy', proxy_url])
                
                # 添加URL
                cmd.append(url)
                
                self.logger.info(f"執行下載命令: {' '.join(cmd)}")
                
                # 執行命令
                self.download_process = create_popen(cmd)
                
                # 讀取輸出
                for line in self.download_process.stdout:
                    if not self.is_downloading:
                        self.download_process.terminate()
                        self.logger.info("下載被用戶取消")
                        break
                    
                    self.parse_progress(line)
                
                # 等待進程結束
                return_code = self.download_process.wait()
                if return_code != 0:
                    success = False
                    # 如果有收集到的錯誤信息，使用它們構建詳細的錯誤消息
                    if self.current_error_lines:
                        error_message = "\n".join(self.current_error_lines)
                        # 检测是否是 JavaScript 运行时错误
                        if 'No supported JavaScript runtime' in error_message or 'JavaScript runtime' in error_message:
                            from src.utils.platform import find_javascript_runtime
                            if not find_javascript_runtime():
                                error_message = (
                                    "缺少 JavaScript 运行时\n\n"
                                    "YouTube 现在需要 JavaScript 运行时来提取视频信息。\n\n"
                                    "请安装 Node.js：\n"
                                    "1. 访问 https://nodejs.org/\n"
                                    "2. 下载并安装最新 LTS 版本\n"
                                    "3. 重启应用程序\n\n"
                                    "或者安装 Deno：\n"
                                    "1. 访问 https://deno.land/\n"
                                    "2. 按照说明安装\n"
                                    "3. 重启应用程序"
                                )
                        self.logger.error(f"下載失败 - URL: {url}, 返回碼: {return_code}, 錯誤信息: {error_message}")
                    else:
                        error_message = f"下載失败，返回碼: {return_code}"
                        self.logger.error(f"下載失败 - URL: {url}, 返回碼: {return_code}")
                    break
                
                # 記錄下載完成
                duration = time.time() - self.start_time
                self.logger.info(f"下載完成 - URL: {url}, 保存路径: {output_dir}, 耗時: {duration:.2f}秒")
        
        except Exception as e:
            success = False
            error_message = str(e)
            self.logger.error(f"下載過程中發生錯誤: {str(e)}", exc_info=True)
            if self.error_callback:
                self.error_callback(f"下載過程中發生錯誤: {str(e)}")
        
        finally:
            self.is_downloading = False
            self.download_process = None
            
            # 調用完成回調
            if self.completion_callback:
                self.completion_callback(success, output_dir if success else error_message)
    
    def cancel_download(self) -> None:
        """取消下載"""
        if not self.is_downloading:
            return
        
        self.logger.info("用戶取消下載")
        self.is_downloading = False
        
        # 終止下載進程
        if self.download_process:
            try:
                self.download_process.terminate()
                self.logger.info("已終止下載進程")
            except:
                self.logger.error("終止下載進程失败", exc_info=True)
        
        # 等待下載線程結束
        if self.download_thread and self.download_thread.is_alive():
            self.download_thread.join(timeout=1.0)
        
        # 重置狀態
        self.current_progress = 0
        self.download_speed = "0 KiB/s"
        self.eta = "00:00"
        
        # 發布取消事件
        event_bus.emit(Events.DOWNLOAD_CANCELLED, url=self.current_url)
        
        # 調用完成回調
        if self.completion_callback:
            self.completion_callback(False, "下載已取消")


# ============ 下载任务数据类 ============

@dataclass
class DownloadTask:
    """下载任务"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    title: str = ""
    output_dir: str = ""
    video_format_id: str = "best"
    audio_format_id: str = "best"
    use_cookies: bool = False
    cookies_file: Optional[str] = None
    prefer_mp4: bool = True
    no_playlist: bool = True
    proxy_url: Optional[str] = None
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    error_message: str = ""
    file_path: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def get_format_id(self) -> str:
        """获取合并的格式ID"""
        if self.audio_format_id and self.audio_format_id != "best":
            return f"{self.video_format_id}+{self.audio_format_id}"
        return self.video_format_id


# ============ 增强版下载器 ============

class EnhancedDownloader:
    """
    增强版下载器
    
    特性：
    - 事件驱动架构
    - 支持并发下载
    - 任务管理
    - 更好的错误处理
    """
    
    def __init__(self, max_concurrent: int = 2):
        """
        初始化增强版下载器
        
        Args:
            max_concurrent: 最大并发下载数
        """
        self.logger = LoggerManager().get_logger()
        self.yt_dlp_path = str(get_yt_dlp_path())
        self.ffmpeg_path = str(get_ffmpeg_path())
        self.max_concurrent = max_concurrent
        
        # 任务管理
        self._tasks: Dict[str, DownloadTask] = {}
        self._active_tasks: Dict[str, threading.Thread] = {}
        self._lock = threading.RLock()
        
        # 状态
        self._running = True
    
    def create_task(self, options: DownloadOptions) -> DownloadTask:
        """
        创建下载任务
        
        Args:
            options: 下载选项
            
        Returns:
            下载任务
        """
        task = DownloadTask(
            url=options.url,
            output_dir=options.output_dir,
            video_format_id=options.video_format_id,
            audio_format_id=options.audio_format_id,
            use_cookies=options.use_cookies,
            cookies_file=options.cookies_file,
            prefer_mp4=options.prefer_mp4,
            no_playlist=options.no_playlist,
            proxy_url=options.proxy_url
        )
        
        with self._lock:
            self._tasks[task.id] = task
        
        self.logger.info(f"创建下载任务: {task.id} - {options.url}")
        return task
    
    def start_task(self, task_id: str) -> bool:
        """
        开始下载任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功开始
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                self.logger.error(f"任务不存在: {task_id}")
                return False
            
            if task.status == DownloadStatus.DOWNLOADING:
                self.logger.warning(f"任务已在下载中: {task_id}")
                return False
            
            if len(self._active_tasks) >= self.max_concurrent:
                task.status = DownloadStatus.QUEUED
                self.logger.info(f"任务加入队列: {task_id}")
                return True
            
            # 开始下载
            task.status = DownloadStatus.DOWNLOADING
            task.started_at = datetime.now()
            
            thread = threading.Thread(
                target=self._download_worker,
                args=(task,),
                daemon=True
            )
            self._active_tasks[task_id] = thread
            thread.start()
            
            # 发布事件
            event_bus.emit(Events.DOWNLOAD_STARTED, task_id=task_id, url=task.url)
            
            return True
    
    def _download_worker(self, task: DownloadTask):
        """下载工作线程"""
        try:
            self.logger.info(f"开始下载: {task.url}")
            
            # 确保输出目录存在
            os.makedirs(task.output_dir, exist_ok=True)
            
            # 构建命令
            cmd = [
                self.yt_dlp_path,
                '-f', task.get_format_id(),
                '-o', os.path.join(task.output_dir, '%(title)s.%(ext)s'),
                '--newline',
                '--ffmpeg-location', self.ffmpeg_path,
            ]
            
            # 添加 JavaScript 运行时支持
            js_runtime_args = get_js_runtime_args()
            if js_runtime_args:
                cmd.extend(js_runtime_args)
            
            if task.no_playlist:
                cmd.append('--no-playlist')
            
            if task.prefer_mp4:
                cmd.extend(['--merge-output-format', 'mp4'])
            
            if task.use_cookies and task.cookies_file:
                cmd.extend(['--cookies', task.cookies_file])
            
            if task.proxy_url:
                cmd.extend(['--proxy', task.proxy_url])
            
            cmd.append(task.url)
            
            # 执行下载
            process = create_popen(cmd)
            
            for line in process.stdout:
                if task.status == DownloadStatus.CANCELLED:
                    process.terminate()
                    break
                
                self._parse_progress(task, line)
            
            return_code = process.wait()
            
            if task.status == DownloadStatus.CANCELLED:
                raise DownloadCancelledError()
            
            if return_code != 0:
                raise DownloadError(f"下载失败，返回码: {return_code}")
            
            # 下载成功
            task.status = DownloadStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 100.0
            
            event_bus.emit(
                Events.DOWNLOAD_COMPLETED,
                task_id=task.id,
                url=task.url,
                file_path=task.file_path
            )
            
            self.logger.info(f"下载完成: {task.url}")
            
        except DownloadCancelledError:
            task.status = DownloadStatus.CANCELLED
            event_bus.emit(Events.DOWNLOAD_CANCELLED, task_id=task.id, url=task.url)
            self.logger.info(f"下载已取消: {task.url}")
            
        except Exception as e:
            task.status = DownloadStatus.FAILED
            task.error_message = str(e)
            event_bus.emit(
                Events.DOWNLOAD_FAILED,
                task_id=task.id,
                url=task.url,
                error=str(e)
            )
            self.logger.error(f"下载失败: {task.url} - {e}")
            
        finally:
            with self._lock:
                self._active_tasks.pop(task.id, None)
                self._try_start_queued()
    
    def _parse_progress(self, task: DownloadTask, line: str):
        """解析进度输出"""
        # 解析进度百分比
        progress_match = re.search(r'(\d+\.\d+)%', line)
        if progress_match:
            task.progress = float(progress_match.group(1))
        
        # 解析下载速度
        speed_match = re.search(r'(\d+\.\d+\s*[KMG]iB/s)', line)
        if speed_match:
            task.speed = speed_match.group(1)
        
        # 解析剩余时间
        eta_match = re.search(r'ETA\s+(\d+:\d+)', line)
        if eta_match:
            task.eta = eta_match.group(1)
        
        # 解析文件名
        dest_match = re.search(r'\[download\]\s+Destination:\s+(.+)', line)
        if dest_match:
            task.file_path = dest_match.group(1).strip()
        
        # 发布进度事件
        event_bus.emit(
            Events.DOWNLOAD_PROGRESS,
            task_id=task.id,
            progress=task.progress,
            speed=task.speed,
            eta=task.eta
        )
    
    def _try_start_queued(self):
        """尝试启动队列中的任务"""
        with self._lock:
            if len(self._active_tasks) >= self.max_concurrent:
                return
            
            for task in self._tasks.values():
                if task.status == DownloadStatus.QUEUED:
                    self.start_task(task.id)
                    break
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            if task.status in (DownloadStatus.COMPLETED, DownloadStatus.CANCELLED):
                return False
            
            task.status = DownloadStatus.CANCELLED
            return True
    
    def pause_task(self, task_id: str) -> bool:
        """暂停任务（标记为暂停，实际会取消当前下载）"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != DownloadStatus.DOWNLOADING:
                return False
            
            task.status = DownloadStatus.PAUSED
            event_bus.emit(Events.DOWNLOAD_PAUSED, task_id=task_id)
            return True
    
    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != DownloadStatus.PAUSED:
                return False
            
            return self.start_task(task_id)
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """获取任务"""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[DownloadTask]:
        """获取所有任务"""
        return list(self._tasks.values())
    
    def get_active_count(self) -> int:
        """获取活跃任务数"""
        return len(self._active_tasks)
    
    def remove_task(self, task_id: str) -> bool:
        """移除任务（仅限已完成/已取消/失败的任务）"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            if task.status in (DownloadStatus.DOWNLOADING, DownloadStatus.QUEUED):
                return False
            
            del self._tasks[task_id]
            return True
    
    def clear_completed(self):
        """清除已完成的任务"""
        with self._lock:
            to_remove = [
                tid for tid, task in self._tasks.items()
                if task.status in (DownloadStatus.COMPLETED, DownloadStatus.CANCELLED, DownloadStatus.FAILED)
            ]
            for tid in to_remove:
                del self._tasks[tid]
    
    def shutdown(self):
        """关闭下载器"""
        self._running = False
        
        # 取消所有活跃任务
        with self._lock:
            for task_id in list(self._active_tasks.keys()):
                self.cancel_task(task_id)


# 创建全局增强版下载器实例
enhanced_downloader = EnhancedDownloader()
