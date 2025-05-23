"""
YouTube Downloader 的配置管理模块
负责处理应用程序配置和设置
"""
import os
import json
import sys
from typing import Dict, Any, Optional


class ConfigManager:
    """配置管理类"""
    
    def __init__(self, config_file: str = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路徑，如果為 None 則使用默認路徑
        """
        # 获取应用程序数据目录
        if sys.platform.startswith('win'):
            app_data_dir = os.path.join(os.environ.get('APPDATA', ''), 'YouTubeDownloader')
        else:
            app_data_dir = os.path.join(os.path.expanduser('~'), '.youtube_downloader')
        
        # 确保目录存在
        os.makedirs(app_data_dir, exist_ok=True)
        
        # 设置配置文件路径
        self.config_file = config_file or os.path.join(app_data_dir, 'config.json')
        
        # 默认配置
        self.default_config = {
            'download_dir': os.path.join(os.path.expanduser('~'), 'Downloads'),
            'use_cookies': False,
            'auto_cookies': False,
            'cookies_file': '',
            'prefer_mp4': True,
            'default_format': 'best',
            'show_notifications': True,
            'check_updates': True,
            'last_yt_dlp_check': 0,
            'last_ffmpeg_check': 0
        }
        
        # 加载配置
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置
        
        Returns:
            配置字典
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 合并默认配置和加载的配置
                merged_config = self.default_config.copy()
                merged_config.update(config)
                return merged_config
            except Exception as e:
                print(f"加载配置文件时发生错误: {str(e)}")
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
        获取配置项
        
        Args:
            key: 配置项键名
            default: 默认值
            
        Returns:
            配置项值
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置项
        
        Args:
            key: 配置项键名
            value: 配置项值
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
        """重置为默认配置"""
        self.config = self.default_config.copy()
