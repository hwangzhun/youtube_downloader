import os
import sys
import json
from typing import Dict, List, Optional
from datetime import datetime

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))  # src/core/video_info
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))  # 项目根目录
if base_dir not in sys.path:
    sys.path.append(base_dir)

from src.core.video_info.format_parser import FormatParser
from src.utils.platform import run_subprocess, get_yt_dlp_path, get_cache_dir, get_js_runtime_args

class VideoInfoCache:
    """视频信息缓存类"""
    
    def __init__(self, cache_dir: str = None):
        """
        初始化缓存
        
        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = cache_dir or str(get_cache_dir() / 'video_info')
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
            print(f"保存缓存失败: {str(e)}")
    
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
            print(f"读取缓存失败: {str(e)}")
            return None


class VideoInfoParser:
    def __init__(self):
        # 获取 yt-dlp 路径
        self.yt_dlp_path = str(get_yt_dlp_path())
        self.cache = VideoInfoCache()
        self.format_parser = FormatParser()

    def is_playlist_url(self, url: str) -> bool:
        """检查URL是否为播放列表"""
        return 'list=' in url or '/playlist' in url
    
    def is_channel_url(self, url: str) -> bool:
        """检查URL是否为频道URL（支持标准频道URL格式和@用户名格式）"""
        # 支持多种频道URL格式：
        # - https://www.youtube.com/channel/CHANNEL_ID
        # - https://www.youtube.com/@USERNAME
        # - https://www.youtube.com/@USERNAME/videos
        return '/channel/' in url or '/@' in url
    
    def get_playlist_videos(self, url: str, use_cookies: bool = False, 
                           cookies_file: str = None, proxy_url: str = None) -> List[Dict]:
        """
        获取播放列表中的所有视频信息
        
        Args:
            url: 播放列表URL
            use_cookies: 是否使用Cookie
            cookies_file: Cookie文件路径
            proxy_url: 代理URL
            
        Returns:
            视频信息列表，每个包含 url, title, duration 等基本信息
        """
        import subprocess
        
        command = [
            self.yt_dlp_path,
            '--flat-playlist',  # 只获取列表，不下载
            '--dump-json',
        ]
        
        # 添加 JavaScript 运行时支持
        js_runtime_args = get_js_runtime_args()
        if js_runtime_args:
            command.extend(js_runtime_args)
        
        if use_cookies and cookies_file:
            command.extend(['--cookies', cookies_file])
        
        if proxy_url:
            command.extend(['--proxy', proxy_url])
        
        # URL 放在最后
        command.append(url)
        
        try:
            result = run_subprocess(command, check=True, timeout=120)
            videos = []
            
            # 输出是多行JSON，每行一个视频
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        video_data = json.loads(line)
                        # 构建完整的视频URL
                        video_id = video_data.get('id', '')
                        video_url = video_data.get('url', '')
                        
                        # 如果没有完整URL，根据ID构建
                        if not video_url and video_id:
                            video_url = f"https://www.youtube.com/watch?v={video_id}"
                        
                        if video_url:
                            videos.append({
                                'url': video_url,
                                'id': video_id,
                                'title': video_data.get('title', '未知标题'),
                                'duration': video_data.get('duration', 0),
                                'uploader': video_data.get('uploader', ''),
                            })
                    except json.JSONDecodeError:
                        continue
            
            return videos
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
            raise Exception(f"获取播放列表失败：{error_msg[:200]}")
        except Exception as e:
            raise Exception(f"获取播放列表失败：{str(e)}")
    
    def get_channel_videos(self, url: str, use_cookies: bool = False,
                          cookies_file: str = None, proxy_url: str = None) -> List[Dict]:
        """
        获取频道中的所有视频信息
        
        Args:
            url: 频道URL（格式：https://www.youtube.com/channel/CHANNEL_ID）
            use_cookies: 是否使用Cookie
            cookies_file: Cookie文件路径
            proxy_url: 代理URL
            
        Returns:
            视频信息列表，每个包含 url, title, duration 等基本信息
        """
        import subprocess
        
        command = [
            self.yt_dlp_path,
            '--flat-playlist',  # 只获取列表，不下载
            '--dump-json',
        ]
        
        # 添加 JavaScript 运行时支持
        js_runtime_args = get_js_runtime_args()
        if js_runtime_args:
            command.extend(js_runtime_args)
        
        if use_cookies and cookies_file:
            command.extend(['--cookies', cookies_file])
        
        if proxy_url:
            command.extend(['--proxy', proxy_url])
        
        # URL 放在最后
        command.append(url)
        
        try:
            result = run_subprocess(command, check=True, timeout=300)  # 频道可能有很多视频，增加超时时间
            videos = []
            
            # 输出是多行JSON，每行一个视频
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        video_data = json.loads(line)
                        # 构建完整的视频URL
                        video_id = video_data.get('id', '')
                        video_url = video_data.get('url', '')
                        
                        # 如果没有完整URL，根据ID构建
                        if not video_url and video_id:
                            video_url = f"https://www.youtube.com/watch?v={video_id}"
                        
                        if video_url:
                            videos.append({
                                'url': video_url,
                                'id': video_id,
                                'title': video_data.get('title', '未知标题'),
                                'duration': video_data.get('duration', 0),
                                'uploader': video_data.get('uploader', ''),
                            })
                    except json.JSONDecodeError:
                        continue
            
            return videos
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
            raise Exception(f"获取频道视频失败：{error_msg[:200]}")
        except Exception as e:
            raise Exception(f"获取频道视频失败：{str(e)}")
    
    def parse_video(self, url: str, use_cookies: bool = False, 
                   cookies_file: str = None, proxy_url: str = None) -> Dict:
        """解析视频信息，优先使用缓存"""
        try:
            # 先尝试从缓存获取
            cached_data = self.cache.load_from_cache(url)
            if cached_data:
                return cached_data
                
            # 如果没有缓存，则解析并保存到缓存
            result = self.get_video_info(url, use_cookies=use_cookies, 
                                       cookies_file=cookies_file, proxy_url=proxy_url)
            if result:
                # 保存到缓存
                self.cache.save_to_cache(url, result)
                return result
            return None
        except Exception as e:
            print(f"错误详情: {str(e)}")
            raise Exception(f"解析失败：{str(e)}")

    def parse_video_info(self, url: str) -> Dict:
        """兼容方法，调用 parse_video"""
        return self.parse_video(url)

    def get_video_info(self, url: str, use_cookies: bool = False, 
                      cookies_file: str = None, proxy_url: str = None) -> Dict:
        """获取视频的详细信息"""
        import subprocess
        
        command = [
            self.yt_dlp_path,
            '--dump-json',
            '--no-playlist',
        ]
        
        # 添加 JavaScript 运行时支持
        js_runtime_args = get_js_runtime_args()
        if js_runtime_args:
            command.extend(js_runtime_args)
        
        if use_cookies and cookies_file:
            command.extend(['--cookies', cookies_file])
        
        if proxy_url:
            command.extend(['--proxy', proxy_url])
        
        # URL 放在最后
        command.append(url)
        
        try:
            result = run_subprocess(command, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            # 获取详细的错误信息
            error_msg = str(e)
            # CalledProcessError 可能包含 stderr 和 stdout 属性
            if hasattr(e, 'stderr') and e.stderr:
                error_msg = e.stderr.strip()
            elif hasattr(e, 'stdout') and e.stdout:
                error_msg = e.stdout.strip()
            # 如果没有详细错误，尝试重新运行以获取错误信息
            if not error_msg or error_msg == str(e):
                try:
                    result_no_check = run_subprocess(command, check=False)
                    if result_no_check.stderr:
                        error_msg = result_no_check.stderr.strip()
                    elif result_no_check.stdout:
                        error_msg = result_no_check.stdout.strip()
                except:
                    pass
            
            # 提取关键错误信息（简化显示）
            if "Private video" in error_msg or "private" in error_msg.lower():
                raise Exception("视频为私密视频，无法访问。请使用 Cookie 或确保您有访问权限。")
            elif "This video is unavailable" in error_msg or "unavailable" in error_msg.lower():
                raise Exception("视频不可用。视频可能已被删除或无法在当前地区访问。")
            elif "Sign in to confirm your age" in error_msg or "age" in error_msg.lower():
                raise Exception("视频需要年龄验证。请使用 Cookie 登录后重试。")
            elif "HTTP Error 403" in error_msg or "403" in error_msg:
                raise Exception("访问被拒绝 (403)。请尝试使用 Cookie 或检查网络。")
            elif "HTTP Error 429" in error_msg or "429" in error_msg:
                raise Exception("请求过于频繁 (429)。请稍后再试。")
            else:
                # 提取前200个字符的错误信息
                short_msg = error_msg[:200] if len(error_msg) > 200 else error_msg
                raise Exception(f"获取视频信息失败：{short_msg}")
        except json.JSONDecodeError as e:
            raise Exception(f"解析视频信息失败（JSON格式错误）：{str(e)}")
        except Exception as e:
            # 如果已经是我们的自定义异常，直接抛出
            if "获取视频信息失败" in str(e) or "解析视频信息失败" in str(e):
                raise
            raise Exception(f"解析视频信息失败：{str(e)}")

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
        print(f"标题: {basic_info['title']}")
        print(f"时长: {parser.format_duration(basic_info['duration'])}")
        print(f"上传者: {basic_info['uploader']}")
        
        # 获取可用格式
        formats = parser.get_available_formats(video_info)
        formatted_formats = parser.get_formatted_formats(formats)
        
        print("\n可用格式:")
        for f in formatted_formats:
            print(f"ID: {f['format_id']} - {f['display']}")
            
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    main() 