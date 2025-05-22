"""
YouTube 視頻下載工具的配置管理模塊
負責處理應用程序配置和設置
"""
import os
import json
import sys
from typing import Dict, Any, Optional


class ConfigManager:
    """配置管理類"""
    
    def __init__(self, config_file: str = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路徑，如果為 None 則使用默認路徑
        """
        # 獲取應用程序數據目錄
        if sys.platform.startswith('win'):
            app_data_dir = os.path.join(os.environ.get('APPDATA', ''), 'YouTubeDownloader')
        else:
            app_data_dir = os.path.join(os.path.expanduser('~'), '.youtube_downloader')
        
        # 確保目錄存在
        os.makedirs(app_data_dir, exist_ok=True)
        
        # 設置配置文件路徑
        self.config_file = config_file or os.path.join(app_data_dir, 'config.json')
        
        # 默認配置
        self.default_config = {
            'download_dir': os.path.join(os.path.expanduser('~'), 'Downloads'),
            'use_cookies': True,
            'auto_cookies': True,
            'cookies_file': '',
            'prefer_mp4': True,
            'default_format': 'best',
            'show_notifications': True,
            'check_updates': True,
            'last_yt_dlp_check': 0,
            'last_ffmpeg_check': 0
        }
        
        # 加載配置
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """
        加載配置
        
        Returns:
            配置字典
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 合併默認配置和加載的配置
                merged_config = self.default_config.copy()
                merged_config.update(config)
                return merged_config
            except Exception as e:
                print(f"加載配置文件時發生錯誤: {str(e)}")
                return self.default_config.copy()
        else:
            return self.default_config.copy()
    
    def save_config(self) -> bool:
        """
        保存配置
        
        Returns:
            是否成功保存
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件時發生錯誤: {str(e)}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        獲取配置項
        
        Args:
            key: 配置項鍵名
            default: 默認值
            
        Returns:
            配置項值
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        設置配置項
        
        Args:
            key: 配置項鍵名
            value: 配置項值
        """
        self.config[key] = value
    
    def update(self, config_dict: Dict[str, Any]) -> None:
        """
        批量更新配置
        
        Args:
            config_dict: 配置字典
        """
        self.config.update(config_dict)
    
    def reset(self) -> None:
        """重置為默認配置"""
        self.config = self.default_config.copy()
