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


class VersionManager:
    """版本管理類"""
    
    def __init__(self, yt_dlp_path: str = None, ffmpeg_path: str = None):
        """
        初始化版本管理器
        
        Args:
            yt_dlp_path: yt-dlp 可執行文件路徑，如果為 None 則使用內置路徑
            ffmpeg_path: ffmpeg 可執行文件路徑，如果為 None 則使用內置路徑
        """
        # 獲取當前腳本所在目錄
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 設置 yt-dlp 和 ffmpeg 路徑
        self.yt_dlp_dir = os.path.join(base_dir, 'resources', 'binaries', 'yt-dlp')
        self.ffmpeg_dir = os.path.join(base_dir, 'resources', 'binaries', 'ffmpeg')
        
        self.yt_dlp_path = yt_dlp_path or os.path.join(self.yt_dlp_dir, 'yt-dlp.exe')
        self.ffmpeg_path = ffmpeg_path or os.path.join(self.ffmpeg_dir, 'ffmpeg.exe')
        
        # GitHub API URLs
        self.yt_dlp_api_url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
        self.ffmpeg_api_url = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"
        
        # 更新狀態
        self.update_in_progress = False
        self.update_progress = 0
        self.update_status = ""
    
    def get_yt_dlp_version(self) -> Tuple[bool, str]:
        """
        獲取當前 yt-dlp 版本
        
        Returns:
            (成功標誌, 版本號或錯誤信息)
        """
        if not os.path.exists(self.yt_dlp_path):
            return False, "yt-dlp 可執行文件不存在"
        
        try:
            cmd = [self.yt_dlp_path, '--version']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, version
            else:
                return False, f"獲取版本失敗: {result.stderr}"
        except Exception as e:
            return False, f"獲取版本時發生錯誤: {str(e)}"
    
    def get_ffmpeg_version(self) -> Tuple[bool, str]:
        """
        獲取當前 ffmpeg 版本
        
        Returns:
            (成功標誌, 版本號或錯誤信息)
        """
        if not os.path.exists(self.ffmpeg_path):
            return False, "ffmpeg 可執行文件不存在"
        
        try:
            cmd = [self.ffmpeg_path, '-version']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # 提取版本號
                version_match = re.search(r'ffmpeg version (\S+)', result.stdout)
                if version_match:
                    version = version_match.group(1)
                    return True, version
                else:
                    return False, "無法解析版本號"
            else:
                return False, f"獲取版本失敗: {result.stderr}"
        except Exception as e:
            return False, f"獲取版本時發生錯誤: {str(e)}"
    
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
            
            # 獲取最新版本信息
            response = requests.get(self.yt_dlp_api_url)
            response.raise_for_status()
            release_info = response.json()
            
            latest_version = release_info['tag_name']
            
            # 比較版本
            if latest_version.strip() != current_version.strip():
                # 查找 Windows 可執行文件下載 URL
                download_url = ""
                for asset in release_info['assets']:
                    if asset['name'] == 'yt-dlp.exe':
                        download_url = asset['browser_download_url']
                        break
                
                if download_url:
                    return True, latest_version, download_url
                else:
                    return False, latest_version, "未找到 Windows 可執行文件下載鏈接"
            else:
                return False, latest_version, "已是最新版本"
        except Exception as e:
            return False, "", f"檢查更新時發生錯誤: {str(e)}"
    
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
            
            # 獲取最新版本信息
            response = requests.get(self.ffmpeg_api_url)
            response.raise_for_status()
            release_info = response.json()
            
            latest_version = release_info['tag_name']
            
            # 查找 Windows 64位 靜態版本下載 URL
            download_url = ""
            for asset in release_info['assets']:
                if 'win64-gpl' in asset['name'] and 'shared' not in asset['name']:
                    download_url = asset['browser_download_url']
                    break
            
            if not download_url:
                return False, latest_version, "未找到適合的下載鏈接"
            
            # 比較版本（簡單比較，實際上應該更複雜）
            if latest_version != current_version:
                return True, latest_version, download_url
            else:
                return False, latest_version, "已是最新版本"
        except Exception as e:
            return False, "", f"檢查更新時發生錯誤: {str(e)}"
    
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
            return False, "更新已在進行中"
        
        self.update_in_progress = True
        self.update_progress = 0
        self.update_status = "正在下載 yt-dlp..."
        
        if progress_callback:
            progress_callback(self.update_progress, self.update_status)
        
        try:
            # 創建臨時文件
            fd, temp_file = tempfile.mkstemp(suffix='.exe', prefix='yt_dlp_')
            os.close(fd)
            
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
            
            # 備份原文件
            if os.path.exists(self.yt_dlp_path):
                backup_file = f"{self.yt_dlp_path}.bak"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(self.yt_dlp_path, backup_file)
            
            # 移動新文件
            self.update_status = "正在安裝 yt-dlp..."
            if progress_callback:
                progress_callback(95, self.update_status)
            
            shutil.move(temp_file, self.yt_dlp_path)
            
            # 獲取新版本
            success, version = self.get_yt_dlp_version()
            
            self.update_in_progress = False
            self.update_progress = 100
            self.update_status = "yt-dlp 更新完成"
            
            if progress_callback:
                progress_callback(self.update_progress, self.update_status)
            
            if success:
                return True, version
            else:
                return False, "更新成功但無法獲取新版本號"
        except Exception as e:
            self.update_in_progress = False
            self.update_status = f"更新失敗: {str(e)}"
            
            if progress_callback:
                progress_callback(0, self.update_status)
            
            return False, f"更新過程中發生錯誤: {str(e)}"
    
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
            return False, "更新已在進行中"
        
        self.update_in_progress = True
        self.update_progress = 0
        self.update_status = "正在下載 ffmpeg..."
        
        if progress_callback:
            progress_callback(self.update_progress, self.update_status)
        
        try:
            # 創建臨時目錄
            temp_dir = tempfile.mkdtemp(prefix='ffmpeg_update_')
            zip_file = os.path.join(temp_dir, 'ffmpeg.zip')
            
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
            
            # 解壓文件
            self.update_status = "正在解壓 ffmpeg..."
            if progress_callback:
                progress_callback(50, self.update_status)
            
            extract_dir = os.path.join(temp_dir, 'extract')
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
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
                raise Exception("在解壓後的文件中未找到 ffmpeg.exe")
            
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
            shutil.copy2(ffmpeg_exe, self.ffmpeg_path)
            
            # 備份和更新 ffprobe.exe
            ffprobe_path = os.path.join(self.ffmpeg_dir, 'ffprobe.exe')
            if ffprobe_exe:
                if os.path.exists(ffprobe_path):
                    backup_file = f"{ffprobe_path}.bak"
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    os.rename(ffprobe_path, backup_file)
                shutil.copy2(ffprobe_exe, ffprobe_path)
            
            # 備份和更新 ffplay.exe
            ffplay_path = os.path.join(self.ffmpeg_dir, 'ffplay.exe')
            if ffplay_exe:
                if os.path.exists(ffplay_path):
                    backup_file = f"{ffplay_path}.bak"
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    os.rename(ffplay_path, backup_file)
                shutil.copy2(ffplay_exe, ffplay_path)
            
            # 清理臨時文件
            self.update_status = "正在清理臨時文件..."
            if progress_callback:
                progress_callback(90, self.update_status)
            
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # 獲取新版本
            success, version = self.get_ffmpeg_version()
            
            self.update_in_progress = False
            self.update_progress = 100
            self.update_status = "ffmpeg 更新完成"
            
            if progress_callback:
                progress_callback(self.update_progress, self.update_status)
            
            if success:
                return True, version
            else:
                return False, "更新成功但無法獲取新版本號"
        except Exception as e:
            self.update_in_progress = False
            self.update_status = f"更新失敗: {str(e)}"
            
            if progress_callback:
                progress_callback(0, self.update_status)
            
            return False, f"更新過程中發生錯誤: {str(e)}"
    
    def download_initial_binaries(self, progress_callback=None) -> Tuple[bool, str]:
        """
        下載初始二進制文件
        
        Args:
            progress_callback: 進度回調函數
            
        Returns:
            (成功標誌, 錯誤信息)
        """
        try:
            # 檢查 yt-dlp
            if not os.path.exists(self.yt_dlp_path):
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
                    return False, "未找到 yt-dlp 下載鏈接"
                
                # 下載 yt-dlp
                if progress_callback:
                    progress_callback(0, "正在下載 yt-dlp...")
                
                os.makedirs(self.yt_dlp_dir, exist_ok=True)
                
                response = requests.get(download_url)
                response.raise_for_status()
                
                with open(self.yt_dlp_path, 'wb') as f:
                    f.write(response.content)
                
                if progress_callback:
                    progress_callback(50, "yt-dlp 下載完成")
            
            # 檢查 ffmpeg
            if not os.path.exists(self.ffmpeg_path):
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
                    return False, "未找到 ffmpeg 下載鏈接"
                
                # 下載並安裝 ffmpeg
                result = self.update_ffmpeg(download_url, progress_callback)
                if not result[0]:
                    return False, result[1]
            
            return True, ""
        except Exception as e:
            return False, f"下載初始二進制文件時發生錯誤: {str(e)}"
