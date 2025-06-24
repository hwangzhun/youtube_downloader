"""
YouTube DownLoader 视频下载核心模块
负责处理视频下载相关的核心功能
"""
import os
import re
import subprocess
import json
import threading
import time
from typing import List, Dict, Tuple, Optional, Callable

# 添加 Windows 特定的导入
if os.name == 'nt':
    import subprocess
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0

from src.utils.logger import LoggerManager

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
        self.yt_dlp_path = yt_dlp_path or os.path.join(base_dir, 'resources', 'binaries', 'yt-dlp', 'yt-dlp.exe')
        self.ffmpeg_path = ffmpeg_path or os.path.join(base_dir, 'resources', 'binaries', 'ffmpeg', 'ffmpeg.exe')
        
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
    
    def extract_video_info(self, url: str, use_cookies: bool = False, cookies_file: str = None) -> Dict:
        """
        提取视频信息
        
        Args:
            url: 视频URL
            use_cookies: 是否使用cookies
            cookies_file: cookies文件路径
            
        Returns:
            视频信息字典
        """
        self.logger.info(f"开始提取视频信息 - URL: {url}, 使用Cookie: {use_cookies}")
        
        cmd = [self.yt_dlp_path, '--dump-json', '--no-playlist', url]
        
        if use_cookies and cookies_file:
            cmd.extend(['--cookies', cookies_file])
            self.logger.info(f"使用Cookie文件: {cookies_file}")
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True,
                creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            video_info = json.loads(result.stdout)
            self.logger.info(f"成功提取视频信息 - 标题: {video_info.get('title', '未知')}")
            return video_info
        except subprocess.CalledProcessError as e:
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
    
    def get_available_formats(self, url: str, use_cookies: bool = False, cookies_file: str = None) -> List[Dict]:
        """
        获取可用的视频格式
        
        Args:
            url: 视频URL
            use_cookies: 是否使用cookies
            cookies_file: cookies文件路径
            
        Returns:
            格式列表，每個格式为一個字典
        """
        self.logger.info(f"开始获取可用格式 - URL: {url}")
        
        video_info = self.extract_video_info(url, use_cookies, cookies_file)
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
                       no_playlist: bool = False) -> None:
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
        """
        if self.is_downloading:
            error_msg = "已有下載任務正在進行"
            self.logger.warning(error_msg)
            if self.error_callback:
                self.error_callback(error_msg)
            return
        
        self.logger.info(f"开始下載任務 - URL數量: {len(urls)}, 格式: {format_id}, 使用Cookie: {use_cookies}, 優先MP4: {prefer_mp4}")
        
        self.is_downloading = True
        self.current_progress = 0
        self.download_speed = "0 KiB/s"
        self.eta = "00:00"
        self.current_video_title = ""
        self.current_video_index = 0
        self.total_videos = len(urls)
        self.start_time = time.time()
        
        # 創建下載線程
        self.download_thread = threading.Thread(
            target=self._download_thread,
            args=(urls, output_dir, format_id, use_cookies, cookies_file, prefer_mp4, no_playlist)
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
                        no_playlist: bool) -> None:
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
                
                # 添加 ffmpeg 位置
                cmd.extend(['--ffmpeg-location', self.ffmpeg_path])
                
                # 如果優先選擇MP4格式
                if prefer_mp4:
                    cmd.extend(['--merge-output-format', 'mp4'])
                
                # 如果使用cookies
                if use_cookies and cookies_file:
                    cmd.extend(['--cookies', cookies_file])
                
                # 添加URL
                cmd.append(url)
                
                self.logger.info(f"執行下載命令: {' '.join(cmd)}")
                
                # 執行命令
                self.download_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
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
        
        # 調用完成回調
        if self.completion_callback:
            self.completion_callback(False, "下載已取消")
