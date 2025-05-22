"""
YouTube 視頻下載核心模塊
負責處理視頻下載相關的核心功能
"""
import os
import re
import subprocess
import json
import threading
from typing import List, Dict, Tuple, Optional, Callable


class VideoDownloader:
    """YouTube 視頻下載器類"""
    
    def __init__(self, yt_dlp_path: str = None, ffmpeg_path: str = None):
        """
        初始化下載器
        
        Args:
            yt_dlp_path: yt-dlp 可執行文件路徑，如果為 None 則使用內置路徑
            ffmpeg_path: ffmpeg 可執行文件路徑，如果為 None 則使用內置路徑
        """
        # 獲取當前腳本所在目錄
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 設置 yt-dlp 和 ffmpeg 路徑
        self.yt_dlp_path = yt_dlp_path or os.path.join(base_dir, 'resources', 'binaries', 'yt-dlp', 'yt-dlp.exe')
        self.ffmpeg_path = ffmpeg_path or os.path.join(base_dir, 'resources', 'binaries', 'ffmpeg', 'ffmpeg.exe')
        
        # 下載狀態
        self.is_downloading = False
        self.current_progress = 0
        self.download_speed = "0 KiB/s"
        self.eta = "00:00"
        self.current_video_title = ""
        self.current_video_index = 0
        self.total_videos = 0
        
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
            progress_callback: 進度回調函數，參數為(進度百分比, 下載速度, 剩餘時間, 當前視頻標題, 當前視頻索引, 總視頻數)
            completion_callback: 完成回調函數，參數為(是否成功, 輸出目錄)
            error_callback: 錯誤回調函數，參數為(錯誤信息)
        """
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.error_callback = error_callback
    
    def extract_video_info(self, url: str, use_cookies: bool = False, cookies_file: str = None) -> Dict:
        """
        提取視頻信息
        
        Args:
            url: 視頻URL
            use_cookies: 是否使用cookies
            cookies_file: cookies文件路徑
            
        Returns:
            視頻信息字典
        """
        cmd = [self.yt_dlp_path, '--dump-json', '--no-playlist', url]
        
        if use_cookies and cookies_file:
            cmd.extend(['--cookies', cookies_file])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            if self.error_callback:
                self.error_callback(f"提取視頻信息失敗: {e.stderr}")
            return {}
        except json.JSONDecodeError:
            if self.error_callback:
                self.error_callback("解析視頻信息失敗")
            return {}
    
    def get_available_formats(self, url: str, use_cookies: bool = False, cookies_file: str = None) -> List[Dict]:
        """
        獲取可用的視頻格式
        
        Args:
            url: 視頻URL
            use_cookies: 是否使用cookies
            cookies_file: cookies文件路徑
            
        Returns:
            格式列表，每個格式為一個字典
        """
        video_info = self.extract_video_info(url, use_cookies, cookies_file)
        if not video_info:
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
        
        return result
    
    def parse_progress(self, line: str) -> None:
        """
        解析進度輸出
        
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
        
        # 解析當前視頻標題
        title_match = re.search(r'\[download\]\s+Destination:\s+(.+)', line)
        if title_match:
            self.current_video_title = os.path.basename(title_match.group(1))
        
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
                       prefer_mp4: bool = True) -> None:
        """
        下載視頻
        
        Args:
            urls: 視頻URL列表
            output_dir: 輸出目錄
            format_id: 格式ID
            use_cookies: 是否使用cookies
            cookies_file: cookies文件路徑
            prefer_mp4: 是否優先選擇MP4格式
        """
        if self.is_downloading:
            if self.error_callback:
                self.error_callback("已有下載任務正在進行")
            return
        
        self.is_downloading = True
        self.current_progress = 0
        self.download_speed = "0 KiB/s"
        self.eta = "00:00"
        self.current_video_title = ""
        self.current_video_index = 0
        self.total_videos = len(urls)
        
        # 創建下載線程
        self.download_thread = threading.Thread(
            target=self._download_thread,
            args=(urls, output_dir, format_id, use_cookies, cookies_file, prefer_mp4)
        )
        self.download_thread.daemon = True
        self.download_thread.start()
    
    def _download_thread(self, 
                        urls: List[str], 
                        output_dir: str, 
                        format_id: str, 
                        use_cookies: bool, 
                        cookies_file: str,
                        prefer_mp4: bool) -> None:
        """
        下載線程
        
        Args:
            urls: 視頻URL列表
            output_dir: 輸出目錄
            format_id: 格式ID
            use_cookies: 是否使用cookies
            cookies_file: cookies文件路徑
            prefer_mp4: 是否優先選擇MP4格式
        """
        success = True
        error_message = ""
        
        try:
            # 確保輸出目錄存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 處理每個URL
            for i, url in enumerate(urls):
                if not self.is_downloading:
                    break
                
                self.current_video_index = i + 1
                
                # 構建命令
                cmd = [
                    self.yt_dlp_path,
                    '-f', format_id,
                    '-o', os.path.join(output_dir, '%(title)s.%(ext)s'),
                    '--newline',
                ]
                
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
                
                # 執行命令
                self.download_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # 讀取輸出
                for line in self.download_process.stdout:
                    if not self.is_downloading:
                        self.download_process.terminate()
                        break
                    
                    self.parse_progress(line)
                
                # 等待進程結束
                return_code = self.download_process.wait()
                if return_code != 0:
                    success = False
                    error_message = f"下載失敗，返回碼: {return_code}"
                    break
        
        except Exception as e:
            success = False
            error_message = str(e)
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
        
        self.is_downloading = False
        
        # 終止下載進程
        if self.download_process:
            try:
                self.download_process.terminate()
            except:
                pass
        
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
