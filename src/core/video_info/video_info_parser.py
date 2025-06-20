import os
import sys
import json
import subprocess
from typing import Dict, List, Optional
from datetime import datetime
from src.utils.logger import LoggerManager

logger = LoggerManager().get_logger()

# 添加 Windows 特定的导入
if os.name == 'nt':
    import subprocess
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))  # src/core/video_info
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))  # 项目根目录
if base_dir not in sys.path:
    sys.path.append(base_dir)

from src.core.video_info.format_parser import FormatParser

class VideoInfoCache:
    """视频信息缓存类"""
    
    def __init__(self, cache_dir: str = "cache"):
        """
        初始化缓存
        
        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = cache_dir
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _get_cache_file(self, url: str) -> str:
        """获取缓存文件路径"""
        # 使用URL的哈希值作为文件名
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.json")
    
    def save_to_cache(self, url: str, data: Dict):
        """保存数据到缓存"""
        cache_file = self._get_cache_file(url)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'data': data
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存失败: {str(e)}")
    
    def load_from_cache(self, url: str, max_age_hours: int = 24) -> Optional[Dict]:
        """从缓存加载数据"""
        cache_file = self._get_cache_file(url)
        if not os.path.exists(cache_file):
            return None
            
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            # 检查缓存是否过期
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if (datetime.now() - cache_time).total_seconds() > max_age_hours * 3600:
                return None
                
            return cache_data['data']
        except Exception as e:
            logger.error(f"读取缓存失败: {str(e)}")
            return None


class VideoInfoParser:
    def __init__(self):
        # 获取基础目录
        current_dir = os.path.dirname(os.path.abspath(__file__))  # src/core/video_info
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))  # 项目根目录
        logger.debug(f"基础目录: {base_dir}")
        self.yt_dlp_path = os.path.join(base_dir, 'resources', 'binaries', 'yt-dlp', 'yt-dlp.exe')
        logger.debug(f"yt-dlp路径: {self.yt_dlp_path}")
        logger.debug(f"文件是否存在: {os.path.exists(self.yt_dlp_path)}")
        self.cache = VideoInfoCache()
        self.format_parser = FormatParser()

    def parse_video(self, url: str) -> Dict:
        """解析视频信息，优先使用缓存"""
        try:
            # 先尝试从缓存获取
            cached_data = self.cache.load_from_cache(url)
            if cached_data:
                return cached_data
                
            # 如果没有缓存，则解析并保存到缓存
            result = self.get_video_info(url)
            if result:
                # 保存到缓存
                self.cache.save_to_cache(url, result)
                return result
            return None
        except Exception as e:
            logger.error(f"错误详情: {str(e)}")
            raise Exception(f"解析失败：{str(e)}")

    def parse_video_info(self, url: str) -> Dict:
        """兼容方法，调用 parse_video"""
        return self.parse_video(url)

    def get_video_info(self, url: str) -> Dict:
        """获取视频的详细信息"""
        command = [
            self.yt_dlp_path,
            '--dump-json',
            '--no-playlist',
            url
        ]
        
        try:
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=True,
                creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            raise Exception(f"获取视频信息失败：{str(e)}")
        except json.JSONDecodeError:
            raise Exception("解析视频信息失败")

    def get_available_formats(self, video_info: Dict) -> List[Dict]:
        """获取可用的视频格式"""
        return self.format_parser.get_available_formats(video_info)

    def get_basic_info(self, video_info: Dict) -> Dict:
        """获取视频的基本信息"""
        if not video_info:
            return {
                'title': '未知标题',
                'duration': 0,
                'uploader': '未知上传者',
                'thumbnail': '',
                'description': '',
                'view_count': 0,
                'like_count': 0
            }
            
        return {
            'title': video_info.get('title', '未知标题'),
            'duration': video_info.get('duration', 0),
            'uploader': video_info.get('uploader', '未知上传者'),
            'thumbnail': video_info.get('thumbnail', ''),
            'description': video_info.get('description', ''),
            'view_count': video_info.get('view_count', 0),
            'like_count': video_info.get('like_count', 0)
        }

    def format_duration(self, seconds: Optional[int]) -> str:
        """将秒数转换为时分秒格式"""
        return self.format_parser.format_duration(seconds)

    def format_filesize(self, size: Optional[int]) -> str:
        """将文件大小转换为可读格式"""
        return self.format_parser.format_filesize(size)

    def format_bitrate(self, bitrate: Optional[float]) -> str:
        """将比特率转换为可读格式"""
        return self.format_parser.format_bitrate(bitrate)

    def format_samplerate(self, samplerate: Optional[int]) -> str:
        """将采样率转换为可读格式"""
        return self.format_parser.format_samplerate(samplerate)

    def get_formatted_formats(self, formats: List[Dict]) -> List[Dict]:
        """格式化格式信息，使其更易读"""
        return self.format_parser.get_formatted_formats(formats)

    def clear_cache(self):
        """清除缓存"""
        import shutil
        try:
            shutil.rmtree("cache")
            os.makedirs("cache")
            return True
        except Exception:
            return False

def main():
    # 测试代码
    parser = VideoInfoParser()
    try:
        # 替换为实际的视频URL
        url = "https://youtu.be/0gNva2bWPoM?si=u5gVbpkutGa6UZFS"
        video_info = parser.parse_video(url)
        
        # 获取基本信息
        basic_info = parser.get_basic_info(video_info)
        logger.info(f"标题: {basic_info['title']}")
        logger.info(f"时长: {parser.format_duration(basic_info['duration'])}")
        logger.info(f"上传者: {basic_info['uploader']}")
        
        # 获取可用格式
        formats = parser.get_available_formats(video_info)
        formatted_formats = parser.get_formatted_formats(formats)
        
        logger.info("\n可用格式:")
        for f in formatted_formats:
            logger.info(f"ID: {f['format_id']} - {f['display']}")
            
    except Exception as e:
        logger.error(f"错误: {str(e)}")

if __name__ == "__main__":
    main() 