"""
YouTube 視頻下載工具的版本管理模塊
負責處理 yt-dlp 和 ffmpeg 的版本檢查和更新
"""
import os
import sys
import subprocess
import re
import json
import time
import tempfile
import shutil
import zipfile
import requests
from typing import Dict, Tuple, Optional, List

# 添加 Windows 特定的导入
if os.name == 'nt':
    import subprocess
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0

from src.utils.logger import LoggerManager


class VersionManager:
    """版本管理類"""
    
    def __init__(self, yt_dlp_path: str = None, ffmpeg_path: str = None):
        """
        初始化版本管理器
        
        Args:
            yt_dlp_path: yt-dlp 可執行文件路徑，如果為 None 則使用內置路徑
            ffmpeg_path: ffmpeg 可執行文件路徑，如果為 None 則使用內置路徑
        """
        # 初始化日誌
        self.logger = LoggerManager().get_logger()
        
        # 獲取當前腳本所在目錄
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 設置 yt-dlp 和 ffmpeg 路徑
        self.yt_dlp_dir = os.path.join(base_dir, 'resources', 'binaries', 'yt-dlp')
        self.ffmpeg_dir = os.path.join(base_dir, 'resources', 'binaries', 'ffmpeg')
        
        self.yt_dlp_path = yt_dlp_path or os.path.join(self.yt_dlp_dir, 'yt-dlp.exe')
        self.ffmpeg_path = ffmpeg_path or os.path.join(self.ffmpeg_dir, 'ffmpeg.exe')
        
        # 記錄初始化信息
        self.logger.info(f"初始化版本管理器 - yt-dlp路徑: {self.yt_dlp_path}, ffmpeg路徑: {self.ffmpeg_path}")
        
        # GitHub API URLs
        self.yt_dlp_api_url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
        self.ffmpeg_api_url = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"
        
        # 更新狀態
        self.update_in_progress = False
        self.update_progress = 0
        self.update_status = ""
        
        # 檢查並創建必要的目錄
        self._ensure_directories()
    
    def _ensure_directories(self):
        """確保必要的目錄存在"""
        try:
            os.makedirs(self.yt_dlp_dir, exist_ok=True)
            os.makedirs(self.ffmpeg_dir, exist_ok=True)
            self.logger.info("創建必要的目錄")
        except Exception as e:
            self.logger.error(f"創建目錄時發生錯誤: {str(e)}", exc_info=True)
    
    def check_and_download_binaries(self, progress_callback=None) -> Tuple[bool, str]:
        """
        檢查並下載必要的二進制文件
        
        Args:
            progress_callback: 進度回調函數
            
        Returns:
            (成功標誌, 錯誤信息)
        """
        try:
            self.logger.info("開始檢查二進制文件")
            
            # 檢查 yt-dlp
            if not os.path.exists(self.yt_dlp_path):
                self.logger.info("yt-dlp 不存在，開始下載")
                
                # 獲取下載 URL
                response = requests.get(self.yt_dlp_api_url)
                response.raise_for_status()
                release_info = response.json()
                
                download_url = ""
                for asset in release_info['assets']:
                    if asset['name'] == 'yt-dlp.exe':
                        download_url = asset['browser_download_url']
                        break
                
                if not download_url:
                    error_msg = "未找到 yt-dlp 下載鏈接"
                    self.logger.error(error_msg)
                    return False, error_msg
                
                # 下載 yt-dlp
                if progress_callback:
                    progress_callback(0, "正在下載 yt-dlp...")
                
                response = requests.get(download_url)
                response.raise_for_status()
                
                with open(self.yt_dlp_path, 'wb') as f:
                    f.write(response.content)
                
                self.logger.info("yt-dlp 下載完成")
                
                if progress_callback:
                    progress_callback(50, "yt-dlp 下載完成")
            
            # 檢查 ffmpeg
            if not os.path.exists(self.ffmpeg_path):
                self.logger.info("ffmpeg 不存在，開始下載")
                
                # 獲取下載 URL
                response = requests.get(self.ffmpeg_api_url)
                response.raise_for_status()
                release_info = response.json()
                
                download_url = ""
                for asset in release_info['assets']:
                    if 'win64-gpl' in asset['name'] and 'shared' not in asset['name']:
                        download_url = asset['browser_download_url']
                        break
                
                if not download_url:
                    error_msg = "未找到 ffmpeg 下載鏈接"
                    self.logger.error(error_msg)
                    return False, error_msg
                
                # 下載並安裝 ffmpeg
                result = self.update_ffmpeg(download_url, progress_callback)
                if not result[0]:
                    return False, result[1]
            
            self.logger.info("二進制文件檢查完成")
            return True, ""
        except Exception as e:
            error_msg = f"檢查二進制文件時發生錯誤: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def get_yt_dlp_version(self) -> Tuple[bool, str]:
        """
        獲取當前 yt-dlp 版本
        
        Returns:
            (成功標誌, 版本號或錯誤信息)
        """
        if not os.path.exists(self.yt_dlp_path):
            self.logger.warning("yt-dlp 可執行文件不存在")
            return False, "yt-dlp 可執行文件不存在"
        
        try:
            cmd = [self.yt_dlp_path, '--version']
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                self.logger.info(f"獲取 yt-dlp 版本成功: {version}")
                return True, version
            else:
                error_msg = f"獲取版本失敗: {result.stderr}"
                self.logger.error(error_msg)
                return False, error_msg
        except Exception as e:
            error_msg = f"獲取版本時發生錯誤: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def get_ffmpeg_version(self) -> Tuple[bool, str]:
        """
        獲取當前 ffmpeg 版本
        
        Returns:
            (成功標誌, 版本號或錯誤信息)
        """
        if not os.path.exists(self.ffmpeg_path):
            self.logger.warning("ffmpeg 可執行文件不存在")
            return False, "ffmpeg 可執行文件不存在"
        
        try:
            cmd = [self.ffmpeg_path, '-version']
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0:
                # 提取版本號
                version_match = re.search(r'ffmpeg version (\S+)', result.stdout)
                if version_match:
                    version = version_match.group(1)
                    # 移除可能的 'n' 前缀
                    version = version.replace('n', '')
                    self.logger.info(f"獲取 ffmpeg 版本成功: {version}")
                    return True, version
                else:
                    error_msg = "無法解析版本號"
                    self.logger.error(error_msg)
                    return False, error_msg
            else:
                error_msg = f"獲取版本失敗: {result.stderr}"
                self.logger.error(error_msg)
                return False, error_msg
        except Exception as e:
            error_msg = f"獲取版本時發生錯誤: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def check_yt_dlp_update(self) -> Tuple[bool, str, str]:
        """
        檢查 yt-dlp 更新
        
        Returns:
            (有更新標誌, 最新版本號, 下載URL或錯誤信息)
        """
        try:
            # 獲取當前版本
            current_success, current_version = self.get_yt_dlp_version()
            if not current_success:
                return False, "", current_version
            
            self.logger.info(f"檢查 yt-dlp 更新 - 當前版本: {current_version}")
            
            # 獲取最新版本信息
            response = requests.get(self.yt_dlp_api_url)
            response.raise_for_status()
            release_info = response.json()
            
            latest_version = release_info['tag_name']
            self.logger.info(f"yt-dlp 最新版本: {latest_version}")
            
            # 比較版本
            if latest_version.strip() != current_version.strip():
                # 查找 Windows 可執行文件下載 URL
                download_url = ""
                for asset in release_info['assets']:
                    if asset['name'] == 'yt-dlp.exe':
                        download_url = asset['browser_download_url']
                        break
                
                if download_url:
                    self.logger.info(f"發現 yt-dlp 新版本: {latest_version}")
                    return True, latest_version, download_url
                else:
                    error_msg = "未找到 Windows 可執行文件下載鏈接"
                    self.logger.error(error_msg)
                    return False, latest_version, error_msg
            else:
                self.logger.info("yt-dlp 已是最新版本")
                return False, latest_version, "已是最新版本"
        except Exception as e:
            error_msg = f"檢查更新時發生錯誤: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, "", error_msg
    
    def check_ffmpeg_update(self) -> Tuple[bool, str, str]:
        """
        檢查 ffmpeg 更新
        
        Returns:
            (有更新標誌, 最新版本號, 下載URL或錯誤信息)
        """
        try:
            # 獲取當前版本
            current_success, current_version = self.get_ffmpeg_version()
            if not current_success:
                return False, "", current_version
            
            self.logger.info(f"檢查 ffmpeg 更新 - 當前版本: {current_version}")
            
            # 獲取最新版本信息
            response = requests.get(self.ffmpeg_api_url)
            response.raise_for_status()
            release_info = response.json()
            
            # 从发布信息中提取版本号
            latest_version = release_info['tag_name'].replace('n', '')  # 移除 'n' 前缀
            self.logger.info(f"ffmpeg 最新版本: {latest_version}")
            
            # 查找 Windows 64位 靜態版本下載 URL
            download_url = ""
            self.logger.info("开始查找下载链接...")
            
            # 记录所有可用的资源
            for asset in release_info['assets']:
                self.logger.info(f"检查资源: {asset['name']}")
                # 优先选择 win64-gpl 静态版本
                if 'win64-gpl' in asset['name'] and 'shared' not in asset['name'] and 'zip' in asset['name']:
                    download_url = asset['browser_download_url']
                    self.logger.info(f"找到匹配的下载链接: {download_url}")
                    break
            
            # 如果没有找到合适的链接，尝试其他版本
            if not download_url:
                for asset in release_info['assets']:
                    if 'win64' in asset['name'] and 'gpl' in asset['name'] and 'zip' in asset['name']:
                        download_url = asset['browser_download_url']
                        self.logger.info(f"使用备用下载链接: {download_url}")
                        break
            
            if not download_url:
                error_msg = "未找到適合的下載鏈接"
                self.logger.error(error_msg)
                return False, latest_version, error_msg
            
            # 比較版本（簡單比較，實際上應該更複雜）
            if latest_version != current_version:
                self.logger.info(f"發現 ffmpeg 新版本: {latest_version}")
                return True, latest_version, download_url
            else:
                self.logger.info("ffmpeg 已是最新版本")
                return False, latest_version, "已是最新版本"
        except Exception as e:
            error_msg = f"檢查更新時發生錯誤: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, "", error_msg
    
    def update_yt_dlp(self, download_url: str, progress_callback=None) -> Tuple[bool, str]:
        """
        更新 yt-dlp
        
        Args:
            download_url: 下載URL
            progress_callback: 進度回調函數
            
        Returns:
            (成功標誌, 新版本號或錯誤信息)
        """
        if self.update_in_progress:
            error_msg = "更新已在進行中"
            self.logger.warning(error_msg)
            return False, error_msg
        
        self.logger.info(f"開始更新 yt-dlp - 下載URL: {download_url}")
        
        self.update_in_progress = True
        self.update_progress = 0
        self.update_status = "正在下載 yt-dlp..."
        
        if progress_callback:
            progress_callback(self.update_progress, self.update_status)
        
        try:
            # 創建臨時文件
            fd, temp_file = tempfile.mkstemp(suffix='.exe', prefix='yt_dlp_')
            os.close(fd)
            self.logger.info(f"創建臨時文件: {temp_file}")
            
            # 下載文件
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            downloaded = 0
            
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            self.update_progress = int(downloaded / total_size * 100)
                            self.update_status = f"正在下載 yt-dlp... {self.update_progress}%"
                            
                            if progress_callback:
                                progress_callback(self.update_progress, self.update_status)
            
            self.logger.info("yt-dlp 下載完成")
            
            # 備份原文件
            if os.path.exists(self.yt_dlp_path):
                backup_file = f"{self.yt_dlp_path}.bak"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(self.yt_dlp_path, backup_file)
                self.logger.info(f"備份原文件: {backup_file}")
            
            # 移動新文件
            self.update_status = "正在安裝 yt-dlp..."
            if progress_callback:
                progress_callback(95, self.update_status)
            
            shutil.move(temp_file, self.yt_dlp_path)
            self.logger.info(f"安裝新文件: {self.yt_dlp_path}")
            
            # 獲取新版本
            success, version = self.get_yt_dlp_version()
            
            self.update_in_progress = False
            self.update_progress = 100
            self.update_status = "yt-dlp 更新完成"
            
            if progress_callback:
                progress_callback(self.update_progress, self.update_status)
            
            if success:
                self.logger.info(f"yt-dlp 更新成功 - 新版本: {version}")
                return True, version
            else:
                error_msg = "更新成功但無法獲取新版本號"
                self.logger.warning(error_msg)
                return False, error_msg
        except Exception as e:
            self.update_in_progress = False
            error_msg = f"更新過程中發生錯誤: {str(e)}"
            self.update_status = error_msg
            
            if progress_callback:
                progress_callback(0, self.update_status)
            
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def update_ffmpeg(self, download_url: str, progress_callback=None) -> Tuple[bool, str]:
        """
        更新 ffmpeg
        
        Args:
            download_url: 下載URL
            progress_callback: 進度回調函數
            
        Returns:
            (成功標誌, 新版本號或錯誤信息)
        """
        if self.update_in_progress:
            error_msg = "更新已在進行中"
            self.logger.warning(error_msg)
            return False, error_msg
        
        self.logger.info(f"開始更新 ffmpeg - 下載URL: {download_url}")
        
        self.update_in_progress = True
        self.update_progress = 0
        self.update_status = "正在下載 ffmpeg..."
        
        if progress_callback:
            progress_callback(self.update_progress, self.update_status)
        
        try:
            # 創建臨時目錄
            temp_dir = tempfile.mkdtemp(prefix='ffmpeg_update_')
            zip_file = os.path.join(temp_dir, 'ffmpeg.zip')
            self.logger.info(f"創建臨時目錄: {temp_dir}")
            
            # 下載文件
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            downloaded = 0
            
            with open(zip_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            self.update_progress = int(downloaded / total_size * 50)  # 下載佔50%進度
                            self.update_status = f"正在下載 ffmpeg... {self.update_progress}%"
                            
                            if progress_callback:
                                progress_callback(self.update_progress, self.update_status)
            
            self.logger.info("ffmpeg 下載完成")
            
            # 解壓文件
            self.update_status = "正在解壓 ffmpeg..."
            if progress_callback:
                progress_callback(50, self.update_status)
            
            extract_dir = os.path.join(temp_dir, 'extract')
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            self.logger.info("ffmpeg 解壓完成")
            
            # 查找 ffmpeg.exe, ffprobe.exe 和 ffplay.exe
            ffmpeg_exe = None
            ffprobe_exe = None
            ffplay_exe = None
            
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower() == 'ffmpeg.exe':
                        ffmpeg_exe = os.path.join(root, file)
                    elif file.lower() == 'ffprobe.exe':
                        ffprobe_exe = os.path.join(root, file)
                    elif file.lower() == 'ffplay.exe':
                        ffplay_exe = os.path.join(root, file)
            
            if not ffmpeg_exe:
                error_msg = "在解壓後的文件中未找到 ffmpeg.exe"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            # 備份原文件
            self.update_status = "正在安裝 ffmpeg..."
            if progress_callback:
                progress_callback(75, self.update_status)
            
            # 確保目標目錄存在
            os.makedirs(self.ffmpeg_dir, exist_ok=True)
            
            # 備份和更新 ffmpeg.exe
            if os.path.exists(self.ffmpeg_path):
                backup_file = f"{self.ffmpeg_path}.bak"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(self.ffmpeg_path, backup_file)
                self.logger.info(f"備份原文件: {backup_file}")
            shutil.copy2(ffmpeg_exe, self.ffmpeg_path)
            self.logger.info(f"安裝新文件: {self.ffmpeg_path}")
            
            # 備份和更新 ffprobe.exe
            ffprobe_path = os.path.join(self.ffmpeg_dir, 'ffprobe.exe')
            if ffprobe_exe:
                if os.path.exists(ffprobe_path):
                    backup_file = f"{ffprobe_path}.bak"
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    os.rename(ffprobe_path, backup_file)
                shutil.copy2(ffprobe_exe, ffprobe_path)
                self.logger.info(f"安裝新文件: {ffprobe_path}")
            
            # 備份和更新 ffplay.exe
            ffplay_path = os.path.join(self.ffmpeg_dir, 'ffplay.exe')
            if ffplay_exe:
                if os.path.exists(ffplay_path):
                    backup_file = f"{ffplay_path}.bak"
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    os.rename(ffplay_path, backup_file)
                shutil.copy2(ffplay_exe, ffplay_path)
                self.logger.info(f"安裝新文件: {ffplay_path}")
            
            # 清理臨時文件
            self.update_status = "正在清理臨時文件..."
            if progress_callback:
                progress_callback(90, self.update_status)
            
            shutil.rmtree(temp_dir, ignore_errors=True)
            self.logger.info("清理臨時文件完成")
            
            # 獲取新版本
            success, version = self.get_ffmpeg_version()
            
            self.update_in_progress = False
            self.update_progress = 100
            self.update_status = "ffmpeg 更新完成"
            
            if progress_callback:
                progress_callback(self.update_progress, self.update_status)
            
            if success:
                self.logger.info(f"ffmpeg 更新成功 - 新版本: {version}")
                return True, version
            else:
                error_msg = "更新成功但無法獲取新版本號"
                self.logger.warning(error_msg)
                return False, error_msg
        except Exception as e:
            self.update_in_progress = False
            error_msg = f"更新過程中發生錯誤: {str(e)}"
            self.update_status = error_msg
            
            if progress_callback:
                progress_callback(0, self.update_status)
            
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    def binaries_exist(self) -> bool:
        """判断yt-dlp和ffmpeg二进制文件是否都存在"""
        return os.path.exists(self.yt_dlp_path) and os.path.exists(self.ffmpeg_path)
