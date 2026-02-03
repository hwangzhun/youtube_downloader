"""
YouTube Downloader 版本管理模块
负责处理 yt-dlp 和 ffmpeg 的版本检查和更新
"""
import os
import sys
import re
import json
import time
import tempfile
import shutil
import zipfile
import requests
from typing import Dict, Tuple, Optional, List

from src.utils.logger import LoggerManager
from src.utils.platform import (
    run_subprocess, get_yt_dlp_path, get_ffmpeg_path, 
    get_binaries_dir, ensure_directory
)


class VersionManager:
    """版本管理类"""
    
    def __init__(self, yt_dlp_path: str = None, ffmpeg_path: str = None):
        """
        初始化版本管理器
        
        Args:
            yt_dlp_path: yt-dlp 可执行文件路径，如果为 None 则使用内置路径
            ffmpeg_path: ffmpeg 可执行文件路径，如果为 None 则使用内置路径
        """
        # 初始化日誌
        self.logger = LoggerManager().get_logger()
        
        # 設置 yt-dlp 和 ffmpeg 路徑
        self.yt_dlp_dir = str(get_binaries_dir() / 'yt-dlp')
        self.ffmpeg_dir = str(get_binaries_dir() / 'ffmpeg')
        
        self.yt_dlp_path = yt_dlp_path or str(get_yt_dlp_path())
        self.ffmpeg_path = ffmpeg_path or str(get_ffmpeg_path())
        
        # 记录初始化信息
        self.logger.info(f"初始化版本管理器 - yt-dlp路径: {self.yt_dlp_path}, ffmpeg路径: {self.ffmpeg_path}")
        
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
        """确保必要的目录存在"""
        try:
            ensure_directory(self.yt_dlp_dir)
            ensure_directory(self.ffmpeg_dir)
            self.logger.info("创建必要的目录")
        except Exception as e:
            self.logger.error(f"创建目录时发生错误: {str(e)}", exc_info=True)
    
    def _create_download_session(self) -> requests.Session:
        """
        创建带有重试机制的下载会话
        
        Returns:
            配置好的 requests.Session
        """
        from urllib3.util.retry import Retry
        from requests.adapters import HTTPAdapter
        
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def check_and_download_binaries(self, progress_callback=None) -> Tuple[bool, str]:
        """
        检查并下载必要的二进制文件
        
        Args:
            progress_callback: 进度回调函数
            
        Returns:
            (成功标志, 错误信息)
        """
        try:
            self.logger.info("开始检查二进制文件")
            
            # 创建下载会话
            session = self._create_download_session()
            
            # 檢查 yt-dlp
            if not os.path.exists(self.yt_dlp_path):
                self.logger.info("yt-dlp 不存在，开始下载")
                
                # 确保目录存在
                os.makedirs(self.yt_dlp_dir, exist_ok=True)
                
                # 获取下载 URL
                response = session.get(self.yt_dlp_api_url, timeout=30)
                response.raise_for_status()
                release_info = response.json()
                
                download_url = ""
                for asset in release_info['assets']:
                    if asset['name'] == 'yt-dlp.exe':
                        download_url = asset['browser_download_url']
                        break
                
                if not download_url:
                    error_msg = "未找到 yt-dlp 下载链接"
                    self.logger.error(error_msg)
                    return False, error_msg
                
                # 下載 yt-dlp
                if progress_callback:
                    progress_callback(0, "正在下载 yt-dlp...")
                
                response = session.get(download_url, timeout=(30, 300))
                response.raise_for_status()
                
                with open(self.yt_dlp_path, 'wb') as f:
                    f.write(response.content)
                
                self.logger.info("yt-dlp 下载完成")
                
                if progress_callback:
                    progress_callback(50, "yt-dlp 下载完成")
            
            # 檢查 ffmpeg
            if not os.path.exists(self.ffmpeg_path):
                self.logger.info("ffmpeg 不存在，开始下载")
                
                # 获取下载 URL
                response = session.get(self.ffmpeg_api_url, timeout=30)
                response.raise_for_status()
                release_info = response.json()
                
                download_url = ""
                for asset in release_info['assets']:
                    if 'win64-gpl' in asset['name'] and 'shared' not in asset['name']:
                        download_url = asset['browser_download_url']
                        break
                
                if not download_url:
                    error_msg = "未找到 ffmpeg 下载链接"
                    self.logger.error(error_msg)
                    return False, error_msg
                
                # 下载并安装 ffmpeg
                result = self.update_ffmpeg(download_url, progress_callback)
                if not result[0]:
                    return False, result[1]
            
            self.logger.info("二进制文件检查完成")
            return True, ""
        except Exception as e:
            error_msg = f"检查二进制文件时发生错误: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def get_yt_dlp_version(self) -> Tuple[bool, str]:
        """
        获取当前 yt-dlp 版本
        
        Returns:
            (成功标志, 版本号或错误信息)
        """
        if not os.path.exists(self.yt_dlp_path):
            self.logger.warning("yt-dlp 可执行文件不存在")
            return False, "yt-dlp 可执行文件不存在"
        
        try:
            cmd = [self.yt_dlp_path, '--version']
            result = run_subprocess(cmd)
            
            if result.returncode == 0:
                version = result.stdout.strip()
                self.logger.info(f"获取 yt-dlp 版本成功: {version}")
                return True, version
            else:
                error_msg = f"获取版本失败: {result.stderr}"
                self.logger.error(error_msg)
                return False, error_msg
        except Exception as e:
            error_msg = f"获取版本时发生错误: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def get_ffmpeg_version(self) -> Tuple[bool, str]:
        """
        获取当前 ffmpeg 版本
        
        Returns:
            (成功标志, 版本号或错误信息)
        """
        if not os.path.exists(self.ffmpeg_path):
            self.logger.warning("ffmpeg 可执行文件不存在")
            return False, "ffmpeg 可执行文件不存在"
        
        try:
            cmd = [self.ffmpeg_path, '-version']
            result = run_subprocess(cmd)
            
            if result.returncode == 0:
                # 提取版本號
                version_match = re.search(r'ffmpeg version (\S+)', result.stdout)
                if version_match:
                    version = version_match.group(1)
                    # 移除可能的 'n' 前缀
                    version = version.replace('n', '')
                    self.logger.info(f"获取 ffmpeg 版本成功: {version}")
                    return True, version
                else:
                    error_msg = "无法解析版本号"
                    self.logger.error(error_msg)
                    return False, error_msg
            else:
                error_msg = f"获取版本失败: {result.stderr}"
                self.logger.error(error_msg)
                return False, error_msg
        except Exception as e:
            error_msg = f"获取版本时发生错误: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def check_yt_dlp_update(self) -> Tuple[bool, str, str]:
        """
        检查 yt-dlp 更新
        
        Returns:
            (有更新标志, 最新版本号, 下载URL或错误信息)
        """
        try:
            # 获取当前版本
            current_success, current_version = self.get_yt_dlp_version()
            
            if current_success:
                self.logger.info(f"检查 yt-dlp 更新 - 当前版本: {current_version}")
            else:
                self.logger.info("yt-dlp 未安装，将获取最新版本下载链接")
                current_version = ""
            
            # 獲取最新版本信息
            response = requests.get(self.yt_dlp_api_url)
            response.raise_for_status()
            release_info = response.json()
            
            latest_version = release_info['tag_name']
            self.logger.info(f"yt-dlp 最新版本: {latest_version}")
            
            # 保存 release_info 供后续获取 release notes
            self._yt_dlp_release_info = release_info
            
            # 查找 Windows 可执行文件下载 URL
            download_url = ""
            for asset in release_info['assets']:
                if asset['name'] == 'yt-dlp.exe':
                    download_url = asset['browser_download_url']
                    break
            
            if not download_url:
                error_msg = "未找到 Windows 可执行文件下载链接"
                self.logger.error(error_msg)
                return False, latest_version, error_msg
            
            # 如果组件未安装，返回需要下载
            if not current_success:
                self.logger.info(f"yt-dlp 未安装，需要下载: {latest_version}")
                return True, latest_version, download_url
            
            # 比較版本
            if latest_version.strip() != current_version.strip():
                self.logger.info(f"发现 yt-dlp 新版本: {latest_version}")
                return True, latest_version, download_url
            else:
                self.logger.info("yt-dlp 已是最新版本")
                return False, latest_version, "已是最新版本"
        except Exception as e:
            error_msg = f"检查更新时发生错误: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, "", error_msg
    
    def get_yt_dlp_release_notes(self) -> str:
        """
        获取 yt-dlp 的 Release Notes
        
        Returns:
            Release Notes 内容
        """
        try:
            if hasattr(self, '_yt_dlp_release_info') and self._yt_dlp_release_info:
                body = self._yt_dlp_release_info.get('body', '')
                # 截取前 1000 个字符，避免太长
                if len(body) > 1000:
                    body = body[:1000] + "\n..."
                return body
            
            # 如果没有缓存，重新获取
            response = requests.get(self.yt_dlp_api_url)
            response.raise_for_status()
            release_info = response.json()
            body = release_info.get('body', '')
            if len(body) > 1000:
                body = body[:1000] + "\n..."
            return body
        except Exception as e:
            self.logger.error(f"获取 yt-dlp Release Notes 失败: {str(e)}")
            return "无法获取更新说明"
    
    def get_ffmpeg_release_notes(self) -> str:
        """
        获取 ffmpeg 的 Release Notes
        
        Returns:
            Release Notes 内容
        """
        try:
            if hasattr(self, '_ffmpeg_release_info') and self._ffmpeg_release_info:
                body = self._ffmpeg_release_info.get('body', '')
                if len(body) > 1000:
                    body = body[:1000] + "\n..."
                return body
            
            # 如果没有缓存，重新获取
            response = requests.get(self.ffmpeg_api_url)
            response.raise_for_status()
            release_info = response.json()
            body = release_info.get('body', '')
            if len(body) > 1000:
                body = body[:1000] + "\n..."
            return body
        except Exception as e:
            self.logger.error(f"获取 ffmpeg Release Notes 失败: {str(e)}")
            return "无法获取更新说明"
    
    def get_file_size(self, file_path: str) -> str:
        """
        获取文件大小的人类可读格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件大小字符串
        """
        try:
            if not os.path.exists(file_path):
                return "未安装"
            
            size = os.path.getsize(file_path)
            
            # 转换为人类可读格式
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} TB"
        except Exception as e:
            self.logger.error(f"获取文件大小失败: {str(e)}")
            return "未知"
    
    def get_yt_dlp_file_size(self) -> str:
        """获取 yt-dlp 文件大小"""
        return self.get_file_size(self.yt_dlp_path)
    
    def get_ffmpeg_total_size(self) -> str:
        """获取 ffmpeg 目录总大小"""
        try:
            if not os.path.exists(self.ffmpeg_dir):
                return "未安装"
            
            total_size = 0
            for file in ['ffmpeg.exe', 'ffprobe.exe', 'ffplay.exe']:
                file_path = os.path.join(self.ffmpeg_dir, file)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
            
            # 转换为人类可读格式
            for unit in ['B', 'KB', 'MB', 'GB']:
                if total_size < 1024:
                    return f"{total_size:.1f} {unit}"
                total_size /= 1024
            return f"{total_size:.1f} TB"
        except Exception as e:
            self.logger.error(f"获取 ffmpeg 大小失败: {str(e)}")
            return "未知"
    
    def check_ffmpeg_update(self) -> Tuple[bool, str, str]:
        """
        检查 ffmpeg 更新
        
        Returns:
            (有更新标志, 最新版本号, 下载URL或错误信息)
        """
        try:
            # 获取当前版本
            current_success, current_version = self.get_ffmpeg_version()
            
            if current_success:
                self.logger.info(f"检查 ffmpeg 更新 - 当前版本: {current_version}")
            else:
                self.logger.info("ffmpeg 未安装，将获取最新版本下载链接")
                current_version = ""
            
            # 获取最新版本信息
            response = requests.get(self.ffmpeg_api_url)
            response.raise_for_status()
            release_info = response.json()
            
            # 保存 release_info 供后续获取 release notes
            self._ffmpeg_release_info = release_info
            
            # 从发布信息中提取版本号
            latest_version = release_info['tag_name'].replace('n', '')  # 移除 'n' 前缀
            self.logger.info(f"ffmpeg 最新版本: {latest_version}")
            
            # 查找 Windows 64位 静态版本下载 URL
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
                error_msg = "未找到适合的下載鏈接"
                self.logger.error(error_msg)
                return False, latest_version, error_msg
            
            # 如果组件未安装，返回需要下载
            if not current_success:
                self.logger.info(f"ffmpeg 未安装，需要下载: {latest_version}")
                return True, latest_version, download_url
            
            # 比較版本（簡單比較，實際上應該更複雜）
            if latest_version != current_version:
                self.logger.info(f"发现 ffmpeg 新版本: {latest_version}")
                return True, latest_version, download_url
            else:
                self.logger.info("ffmpeg 已是最新版本")
                return False, latest_version, "已是最新版本"
        except Exception as e:
            error_msg = f"检查更新时发生错误: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, "", error_msg
    
    def update_yt_dlp(self, download_url: str, progress_callback=None) -> Tuple[bool, str]:
        """
        更新 yt-dlp
        
        Args:
            download_url: 下载URL
            progress_callback: 进度回调函数
            
        Returns:
            (成功标志, 新版本号或错误信息)
        """
        if self.update_in_progress:
            error_msg = "更新已在进行中"
            self.logger.warning(error_msg)
            return False, error_msg
        
        self.logger.info(f"开始更新 yt-dlp - 下载URL: {download_url}")
        
        self.update_in_progress = True
        self.update_progress = 0
        self.update_status = "正在下载 yt-dlp..."
        
        if progress_callback:
            progress_callback(self.update_progress, self.update_status)
        
        try:
            # 创建临时文件
            fd, temp_file = tempfile.mkstemp(suffix='.exe', prefix='yt_dlp_')
            os.close(fd)
            self.logger.info(f"创建临时文件: {temp_file}")
            
            # 下载文件 - 使用重试机制和超时
            session = self._create_download_session()
            response = session.get(download_url, stream=True, timeout=(30, 300))
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
                            self.update_status = f"正在下载 yt-dlp... {self.update_progress}%"
                            
                            if progress_callback:
                                progress_callback(self.update_progress, self.update_status)
            
            self.logger.info("yt-dlp 下载完成")
            
            # 备份原文件
            if os.path.exists(self.yt_dlp_path):
                backup_file = f"{self.yt_dlp_path}.bak"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(self.yt_dlp_path, backup_file)
                self.logger.info(f"备份原文件: {backup_file}")
            
            # 移动新文件
            self.update_status = "正在安装 yt-dlp..."
            if progress_callback:
                progress_callback(95, self.update_status)
            
            # 确保目标目录存在
            os.makedirs(self.yt_dlp_dir, exist_ok=True)
            
            shutil.move(temp_file, self.yt_dlp_path)
            self.logger.info(f"安装新文件: {self.yt_dlp_path}")
            
            # 获取新版本
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
                error_msg = "更新成功但无法获取新版本号"
                self.logger.warning(error_msg)
                return False, error_msg
        except Exception as e:
            self.update_in_progress = False
            error_msg = f"更新过程中发生错误: {str(e)}"
            self.update_status = error_msg
            
            if progress_callback:
                progress_callback(0, self.update_status)
            
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def update_ffmpeg(self, download_url: str, progress_callback=None) -> Tuple[bool, str]:
        """
        更新 ffmpeg
        
        Args:
            download_url: 下载URL
            progress_callback: 进度回调函数
            
        Returns:
            (成功标志, 新版本号或错误信息)
        """
        if self.update_in_progress:
            error_msg = "更新已在进行中"
            self.logger.warning(error_msg)
            return False, error_msg
        
        self.logger.info(f"开始更新 ffmpeg - 下载URL: {download_url}")
        
        self.update_in_progress = True
        self.update_progress = 0
        self.update_status = "正在下载 ffmpeg..."
        
        if progress_callback:
            progress_callback(self.update_progress, self.update_status)
        
        try:
            # 創建臨時目錄
            temp_dir = tempfile.mkdtemp(prefix='ffmpeg_update_')
            zip_file = os.path.join(temp_dir, 'ffmpeg.zip')
            self.logger.info(f"创建临时目录: {temp_dir}")
            
            # 下载文件 - 使用重试机制和超时
            session = self._create_download_session()
            response = session.get(download_url, stream=True, timeout=(30, 600))  # ffmpeg 文件较大，超时设长一些
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
                            self.update_progress = int(downloaded / total_size * 50)  # 下载占50%进度
                            self.update_status = f"正在下载 ffmpeg... {self.update_progress}%"
                            
                            if progress_callback:
                                progress_callback(self.update_progress, self.update_status)
            
            self.logger.info("ffmpeg 下载完成")
            
            # 解压文件
            self.update_status = "正在解压 ffmpeg..."
            if progress_callback:
                progress_callback(50, self.update_status)
            
            extract_dir = os.path.join(temp_dir, 'extract')
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            self.logger.info("ffmpeg 解压完成")
            
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
                error_msg = "在解压后的文件中未找到 ffmpeg.exe"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            # 备份原文件
            self.update_status = "正在安装 ffmpeg..."
            if progress_callback:
                progress_callback(75, self.update_status)
            
            # 确保目标目录存在
            os.makedirs(self.ffmpeg_dir, exist_ok=True)
            
            # 备份和更新 ffmpeg.exe
            if os.path.exists(self.ffmpeg_path):
                backup_file = f"{self.ffmpeg_path}.bak"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(self.ffmpeg_path, backup_file)
                self.logger.info(f"备份原文件: {backup_file}")
            shutil.copy2(ffmpeg_exe, self.ffmpeg_path)
            self.logger.info(f"安装新文件: {self.ffmpeg_path}")
            
            # 备份和更新 ffprobe.exe
            ffprobe_path = os.path.join(self.ffmpeg_dir, 'ffprobe.exe')
            if ffprobe_exe:
                if os.path.exists(ffprobe_path):
                    backup_file = f"{ffprobe_path}.bak"
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    os.rename(ffprobe_path, backup_file)
                shutil.copy2(ffprobe_exe, ffprobe_path)
                self.logger.info(f"安装新文件: {ffprobe_path}")
            
            # 备份和更新 ffplay.exe
            ffplay_path = os.path.join(self.ffmpeg_dir, 'ffplay.exe')
            if ffplay_exe:
                if os.path.exists(ffplay_path):
                    backup_file = f"{ffplay_path}.bak"
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    os.rename(ffplay_path, backup_file)
                shutil.copy2(ffplay_exe, ffplay_path)
                self.logger.info(f"安装新文件: {ffplay_path}")
            
            # 清理臨時文件
            self.update_status = "正在清理临时文件..."
            if progress_callback:
                progress_callback(90, self.update_status)
            
            shutil.rmtree(temp_dir, ignore_errors=True)
            self.logger.info("清理临时文件完成")
            
            # 获取新版本
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
                error_msg = "更新成功但无法获取新版本号"
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
