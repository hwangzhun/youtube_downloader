"""
YouTube DownLoader Cookie 管理模块
负责处理 Cookie 的获取、导入和使用
增强版：支持加密存储和安全内存清理
"""
import os
import tempfile
import shutil
import secrets
import base64
import hashlib
import atexit
from typing import Optional, Tuple, Dict, List
from datetime import datetime

from src.utils.platform import run_subprocess, get_yt_dlp_path, get_app_data_dir
from src.utils.logger import LoggerManager
from src.core.event_bus import event_bus, Events
from src.core.exceptions import CookieError, CookieNotFoundError, CookieInvalidError


class SecureCookieStorage:
    """
    安全 Cookie 存储
    
    特性：
    - 可选的 XOR 加密（简单混淆）
    - 安全的内存清理
    - 文件权限控制
    """
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        初始化安全存储
        
        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = storage_dir or str(get_app_data_dir() / 'cookies')
        self._ensure_storage_dir()
        self._key: Optional[bytes] = None
        
    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Windows 上设置隐藏属性
        if os.name == 'nt':
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(self.storage_dir, 0x02)
    
    def _get_key(self) -> bytes:
        """获取加密密钥（基于机器特征）"""
        if self._key is None:
            # 使用机器特征生成密钥
            import platform
            machine_id = f"{platform.node()}-{os.getlogin()}-youtube-downloader"
            self._key = hashlib.sha256(machine_id.encode()).digest()
        return self._key
    
    def _xor_encrypt(self, data: bytes) -> bytes:
        """XOR 加密"""
        key = self._get_key()
        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])
    
    def _xor_decrypt(self, data: bytes) -> bytes:
        """XOR 解密（与加密相同）"""
        return self._xor_encrypt(data)
    
    def save(self, name: str, content: str, encrypt: bool = True) -> str:
        """
        保存 Cookie 内容
        
        Args:
            name: Cookie 名称
            content: Cookie 内容
            encrypt: 是否加密
            
        Returns:
            保存的文件路径
        """
        file_path = os.path.join(self.storage_dir, f"{name}.cookie")
        
        try:
            data = content.encode('utf-8')
            
            if encrypt:
                data = self._xor_encrypt(data)
                # 添加加密标记
                data = b'ENCRYPTED:' + base64.b64encode(data)
            
            with open(file_path, 'wb') as f:
                f.write(data)
            
            # 设置文件权限（仅所有者可读写）
            if os.name != 'nt':
                os.chmod(file_path, 0o600)
            
            return file_path
        except Exception as e:
            raise CookieError(f"保存 Cookie 失败: {e}")
    
    def load(self, name: str) -> str:
        """
        加载 Cookie 内容
        
        Args:
            name: Cookie 名称
            
        Returns:
            Cookie 内容
        """
        file_path = os.path.join(self.storage_dir, f"{name}.cookie")
        
        if not os.path.exists(file_path):
            raise CookieNotFoundError(path=file_path)
        
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # 检查是否加密
            if data.startswith(b'ENCRYPTED:'):
                data = data[10:]  # 移除标记
                data = base64.b64decode(data)
                data = self._xor_decrypt(data)
            
            return data.decode('utf-8')
        except Exception as e:
            raise CookieError(f"加载 Cookie 失败: {e}")
    
    def delete(self, name: str) -> bool:
        """
        删除 Cookie
        
        Args:
            name: Cookie 名称
            
        Returns:
            是否成功删除
        """
        file_path = os.path.join(self.storage_dir, f"{name}.cookie")
        
        if os.path.exists(file_path):
            # 安全删除：先覆写再删除
            try:
                file_size = os.path.getsize(file_path)
                with open(file_path, 'wb') as f:
                    f.write(os.urandom(file_size))
                os.remove(file_path)
                return True
            except Exception:
                try:
                    os.remove(file_path)
                    return True
                except Exception:
                    return False
        return False
    
    def exists(self, name: str) -> bool:
        """检查 Cookie 是否存在"""
        file_path = os.path.join(self.storage_dir, f"{name}.cookie")
        return os.path.exists(file_path)
    
    def list_all(self) -> List[str]:
        """列出所有保存的 Cookie"""
        cookies = []
        for f in os.listdir(self.storage_dir):
            if f.endswith('.cookie'):
                cookies.append(f[:-7])  # 移除 .cookie 后缀
        return cookies
    
    def clear_all(self):
        """清除所有 Cookie"""
        for name in self.list_all():
            self.delete(name)


class CookieManager:
    """
    Cookie 管理类
    
    增强特性：
    - 安全存储支持
    - 事件通知
    - 更好的错误处理
    """
    
    def __init__(self, yt_dlp_path: str = None):
        """
        初始化 Cookie 管理器
        
        Args:
            yt_dlp_path: yt-dlp 可执行文件路径，如果为 None 则使用内置路径
        """
        # 设置 yt-dlp 路径
        self.yt_dlp_path = yt_dlp_path or str(get_yt_dlp_path())
        
        # 临时 Cookie 文件路径
        self.temp_cookie_file = None
        self._temp_files: List[str] = []
        
        # 安全存储
        self.secure_storage = SecureCookieStorage()
        
        # 日志
        self.logger = LoggerManager().get_logger()
        
        # 注册退出清理
        atexit.register(self._cleanup_all_temp_files)
    
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
            
            result = run_subprocess(cmd)
            
            # 檢查是否成功訪問訂閱頁面
            if result.returncode == 0 and 'Subscriptions' in result.stdout:
                return True, ""
            else:
                return False, "Cookie 無法訪問 YouTube 訂閱頁面，可能已過期或無效"
        except Exception as e:
            return False, f"測試 Cookie 時發生錯誤: {str(e)}"
    
    def _cleanup_temp_file(self) -> None:
        """清理临时文件（安全删除）"""
        if self.temp_cookie_file and os.path.exists(self.temp_cookie_file):
            self._secure_delete_file(self.temp_cookie_file)
            self.temp_cookie_file = None
    
    def _cleanup_all_temp_files(self):
        """清理所有临时文件"""
        self._cleanup_temp_file()
        
        for temp_file in self._temp_files[:]:
            if os.path.exists(temp_file):
                self._secure_delete_file(temp_file)
            self._temp_files.remove(temp_file)
    
    def _secure_delete_file(self, file_path: str):
        """
        安全删除文件（覆写后删除）
        
        Args:
            file_path: 文件路径
        """
        try:
            if os.path.exists(file_path):
                # 获取文件大小
                file_size = os.path.getsize(file_path)
                
                # 用随机数据覆写文件
                with open(file_path, 'wb') as f:
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
                
                # 删除文件
                os.remove(file_path)
                self.logger.debug(f"安全删除临时文件: {file_path}")
        except Exception as e:
            self.logger.warning(f"安全删除文件失败: {file_path} - {e}")
            try:
                os.remove(file_path)
            except Exception:
                pass
    
    def _register_temp_file(self, file_path: str):
        """注册临时文件以便清理"""
        if file_path not in self._temp_files:
            self._temp_files.append(file_path)
    
    def save_cookie(self, name: str, cookie_file: str, encrypt: bool = True) -> str:
        """
        保存 Cookie 到安全存储
        
        Args:
            name: Cookie 名称
            cookie_file: Cookie 文件路径
            encrypt: 是否加密
            
        Returns:
            保存的路径
        """
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            path = self.secure_storage.save(name, content, encrypt)
            
            event_bus.emit(Events.COOKIE_UPDATED, name=name)
            self.logger.info(f"Cookie 已保存: {name}")
            
            return path
        except Exception as e:
            raise CookieError(f"保存 Cookie 失败: {e}")
    
    def load_saved_cookie(self, name: str) -> Tuple[bool, str, str]:
        """
        从安全存储加载 Cookie
        
        Args:
            name: Cookie 名称
            
        Returns:
            (成功标志, Cookie 文件路径, 错误信息)
        """
        try:
            content = self.secure_storage.load(name)
            
            # 创建临时文件
            fd, temp_file = tempfile.mkstemp(suffix='.txt', prefix='yt_cookies_')
            os.close(fd)
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.temp_cookie_file = temp_file
            self._register_temp_file(temp_file)
            
            return True, temp_file, ""
        except CookieNotFoundError:
            return False, "", "Cookie 不存在"
        except Exception as e:
            return False, "", f"加载 Cookie 失败: {e}"
    
    def delete_saved_cookie(self, name: str) -> bool:
        """
        删除保存的 Cookie
        
        Args:
            name: Cookie 名称
            
        Returns:
            是否成功删除
        """
        if self.secure_storage.delete(name):
            event_bus.emit(Events.COOKIE_CLEARED, name=name)
            self.logger.info(f"Cookie 已删除: {name}")
            return True
        return False
    
    def get_saved_cookies(self) -> List[str]:
        """获取所有保存的 Cookie 名称"""
        return self.secure_storage.list_all()
    
    def get_cookie_info(self, cookie_file: str) -> Dict:
        """
        获取 Cookie 信息
        
        Args:
            cookie_file: Cookie 文件路径
            
        Returns:
            Cookie 信息字典
        """
        info = {
            'path': cookie_file,
            'exists': os.path.exists(cookie_file),
            'size': 0,
            'domains': [],
            'youtube_cookies': 0,
            'modified_at': None
        }
        
        if not info['exists']:
            return info
        
        try:
            stat = os.stat(cookie_file)
            info['size'] = stat.st_size
            info['modified_at'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            with open(cookie_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 统计域名和 YouTube Cookie
            domains = set()
            youtube_count = 0
            
            for line in content.splitlines():
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.split('\t')
                if len(parts) >= 1:
                    domain = parts[0].lstrip('.')
                    domains.add(domain)
                    if 'youtube' in domain.lower():
                        youtube_count += 1
            
            info['domains'] = list(domains)
            info['youtube_cookies'] = youtube_count
            
        except Exception as e:
            self.logger.warning(f"获取 Cookie 信息失败: {e}")
        
        return info
    
    def __del__(self):
        """析构函数，确保临时文件被清理"""
        self._cleanup_all_temp_files()
