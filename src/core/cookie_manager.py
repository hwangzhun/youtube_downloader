"""
YouTube DownLoader Cookie 管理模塊
負責處理 Cookie 的獲取、導入和使用
"""
import os
import subprocess
import re
import json
import tempfile
import shutil
from typing import Optional, Tuple, Dict

# 添加 Windows 特定的导入
if os.name == 'nt':
    import subprocess
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0


class CookieManager:
    """Cookie 管理類"""
    
    def __init__(self, yt_dlp_path: str = None):
        """
        初始化 Cookie 管理器
        
        Args:
            yt_dlp_path: yt-dlp 可執行文件路徑，如果為 None 則使用內置路徑
        """
        # 獲取當前腳本所在目錄
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 設置 yt-dlp 路徑
        self.yt_dlp_path = yt_dlp_path or os.path.join(base_dir, 'resources', 'binaries', 'yt-dlp', 'yt-dlp.exe')
        
        # 臨時 Cookie 文件路徑
        self.temp_cookie_file = None
    
    def auto_extract_cookies(self) -> Tuple[bool, str, str]:
        """
        自動從瀏覽器提取 YouTube Cookie
        
        Returns:
            (成功標誌, Cookie 文件路徑, 錯誤信息)
        """
        # 創建臨時文件
        fd, temp_file = tempfile.mkstemp(suffix='.txt', prefix='yt_cookies_')
        os.close(fd)
        
        # 保存臨時文件路徑
        self.temp_cookie_file = temp_file
        
        # 嘗試從各種瀏覽器提取 Cookie
        browsers = ['chrome', 'firefox', 'edge', 'opera', 'brave', 'chromium']
        success = False
        error_message = "無法從任何瀏覽器提取 Cookie"
        
        for browser in browsers:
            try:
                cmd = [
                    self.yt_dlp_path,
                    '--cookies-from-browser', browser,
                    '--cookies', temp_file,
                    '-o', 'NUL',
                    '--skip-download',
                    'https://www.youtube.com/'
                ]
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True,
                    creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                # 檢查是否成功提取 Cookie
                if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                    success = True
                    error_message = ""
                    break
            except Exception as e:
                error_message = f"提取 Cookie 時發生錯誤: {str(e)}"
        
        if not success:
            # 清理臨時文件
            self._cleanup_temp_file()
        
        return success, temp_file if success else "", error_message
    
    def validate_cookie_file(self, cookie_file: str) -> Tuple[bool, str]:
        """
        驗證 Cookie 文件是否有效
        
        Args:
            cookie_file: Cookie 文件路徑
            
        Returns:
            (是否有效, 錯誤信息)
        """
        if not os.path.exists(cookie_file):
            return False, "Cookie 文件不存在"
        
        if os.path.getsize(cookie_file) == 0:
            return False, "Cookie 文件為空"
        
        # 檢查文件格式是否符合 Netscape cookie 格式
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if not first_line.startswith('# Netscape HTTP Cookie File'):
                    return False, "Cookie 文件格式不正確，應為 Netscape HTTP Cookie 格式"
                
                # 檢查是否包含 youtube.com 的 Cookie
                content = f.read()
                if 'youtube.com' not in content:
                    return False, "Cookie 文件中未找到 YouTube 相關的 Cookie"
            
            return True, ""
        except Exception as e:
            return False, f"讀取 Cookie 文件時發生錯誤: {str(e)}"
    
    def import_cookie_file(self, source_file: str) -> Tuple[bool, str, str]:
        """
        導入外部 Cookie 文件
        
        Args:
            source_file: 源 Cookie 文件路徑
            
        Returns:
            (成功標誌, 導入後的 Cookie 文件路徑, 錯誤信息)
        """
        # 驗證源文件
        valid, error_message = self.validate_cookie_file(source_file)
        if not valid:
            return False, "", error_message
        
        # 創建臨時文件
        fd, temp_file = tempfile.mkstemp(suffix='.txt', prefix='yt_cookies_')
        os.close(fd)
        
        # 保存臨時文件路徑
        self.temp_cookie_file = temp_file
        
        try:
            # 複製源文件到臨時文件
            shutil.copy2(source_file, temp_file)
            return True, temp_file, ""
        except Exception as e:
            self._cleanup_temp_file()
            return False, "", f"導入 Cookie 文件時發生錯誤: {str(e)}"
    
    def test_cookie(self, cookie_file: str) -> Tuple[bool, str]:
        """
        測試 Cookie 是否可用於 YouTube
        
        Args:
            cookie_file: Cookie 文件路徑
            
        Returns:
            (是否可用, 錯誤信息)
        """
        try:
            cmd = [
                self.yt_dlp_path,
                '--cookies', cookie_file,
                '--skip-download',
                '--print', 'title',
                'https://www.youtube.com/feed/subscriptions'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # 檢查是否成功訪問訂閱頁面
            if result.returncode == 0 and 'Subscriptions' in result.stdout:
                return True, ""
            else:
                return False, "Cookie 無法訪問 YouTube 訂閱頁面，可能已過期或無效"
        except Exception as e:
            return False, f"測試 Cookie 時發生錯誤: {str(e)}"
    
    def _cleanup_temp_file(self) -> None:
        """清理臨時文件"""
        if self.temp_cookie_file and os.path.exists(self.temp_cookie_file):
            try:
                os.remove(self.temp_cookie_file)
            except:
                pass
            self.temp_cookie_file = None
    
    def __del__(self):
        """析構函數，確保臨時文件被清理"""
        self._cleanup_temp_file()
