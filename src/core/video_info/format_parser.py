import json
import os
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

from src.utils.platform import get_yt_dlp_path

class FormatParser:
    """格式解析器类"""
    
    def __init__(self):
        # 获取 yt-dlp 路径
        self.yt_dlp_path = str(get_yt_dlp_path())
        
        # 加载编码映射表
        self.codec_mappings = self._load_codec_mappings()

    def _load_codec_mappings(self) -> Dict:
        """加载编码映射表"""
        try:
            mapping_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'codec_mappings.json')
            with open(mapping_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载编码映射表失败: {str(e)}")
            return {"video_codecs": {}, "audio_codecs": {}}

    def get_available_formats(self, video_info: Dict) -> List[Dict]:
        """获取可用的视频格式"""
        if not video_info:
            return []
            
        formats = []
        for fmt in video_info.get('formats', []):
            if not fmt:
                continue
                
            # 检查格式类型
            vcodec = fmt.get('vcodec', 'none')
            acodec = fmt.get('acodec', 'none')
            format_note = fmt.get('format_note', '').lower()
            
            # 检查是否是无效格式（如 storyboard、mhtml 等）
            ext = fmt.get('ext', '').lower()
            if ext in ['mhtml', 'sb3', 'storyboard']:
                continue
                
            # 判断格式类型
            is_audio_only = format_note == 'audio only' or (vcodec == 'none' and acodec != 'none')
            is_video = vcodec != 'none'
            
            # 如果既不是视频也不是音频，则跳过
            if not is_audio_only and not is_video:
                continue
                
            format_info = {
                'format_id': fmt.get('format_id', ''),
                'type': 'audio' if is_audio_only else 'video',
                'resolution': self._get_resolution(fmt),
                'fps': fmt.get('fps', 0) or 0,  # 确保 fps 不为 None
                'vcodec': vcodec,
                'acodec': acodec,
                'abr': fmt.get('abr', 0) or 0,  # 确保 abr 不为 None
                'vbr': fmt.get('vbr', 0) or 0,  # 确保 vbr 不为 None
                'asr': fmt.get('asr', 0) or 0,  # 确保 asr 不为 None
                'filesize': self._calculate_filesize(fmt, video_info.get('duration', 0)),
                'protocol': fmt.get('protocol', ''),
                'has_audio': acodec != 'none',
                'format_note': format_note  # 添加格式说明
            }
            formats.append(format_info)
        
        return formats

    def _calculate_filesize(self, fmt: Dict, duration: float) -> int:
        """计算文件大小（字节）"""
        if not duration:
            return 0
            
        # 获取视频和音频比特率
        vbr = fmt.get('vbr', 0) or 0  # 视频比特率 (kbps)
        abr = fmt.get('abr', 0) or 0  # 音频比特率 (kbps)
        
        # 计算总比特率（转换为字节/秒）
        total_bitrate = (vbr + abr) * 1024 / 8
        
        # 计算文件大小（字节）
        filesize = int(total_bitrate * duration)
        
        return filesize

    def _get_resolution(self, fmt: Dict) -> str:
        """获取分辨率"""
        width = fmt.get('width')
        height = fmt.get('height')
        if width and height and isinstance(width, (int, float)) and isinstance(height, (int, float)):
            return f"{int(width)}x{int(height)}"
        return "unknown"

    def _format_bitrate(self, bitrate: float) -> str:
        """格式化比特率"""
        if not isinstance(bitrate, (int, float)) or bitrate <= 0:
            return ""
        if bitrate < 1000:
            return f"{bitrate:.0f}kbps"
        return f"{bitrate/1000:.1f}Mbps"

    def format_duration(self, seconds: Optional[int]) -> str:
        """将秒数转换为时分秒格式"""
        if not isinstance(seconds, (int, float)) or seconds <= 0:
            return "未知时长"
            
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def format_filesize(self, size: Optional[int]) -> str:
        """将文件大小转换为可读格式"""
        if not isinstance(size, (int, float)) or size <= 0:
            return "未知大小"
            
        size = float(size)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

    def format_bitrate(self, bitrate: Optional[float]) -> str:
        """将比特率转换为可读格式"""
        if not isinstance(bitrate, (int, float)) or bitrate <= 0:
            return ""
            
        bitrate = float(bitrate)
        if bitrate < 1000:
            return f"{bitrate:.0f}kbps"
        return f"{bitrate/1000:.1f}Mbps"

    def format_samplerate(self, samplerate: Optional[int]) -> str:
        """将采样率转换为可读格式"""
        if not isinstance(samplerate, (int, float)) or samplerate <= 0:
            return ""
            
        samplerate = int(samplerate)
        if samplerate < 1000:
            return f"{samplerate}Hz"
        return f"{samplerate/1000:.1f}kHz"

    def _simplify_codec(self, codec: str) -> str:
        """简化编码显示，使用防御性编程处理未知编码"""
        if not codec or not isinstance(codec, str):
            return "未知编码"
            
        codec = codec.lower()  # 转换为小写以统一处理
            
        # 检查视频编码
        for prefix, name in self.codec_mappings.get('video_codecs', {}).items():
            if codec.startswith(prefix):
                return name
                
        # 检查音频编码
        for prefix, name in self.codec_mappings.get('audio_codecs', {}).items():
            if codec.startswith(prefix):
                return name
                
        # 如果找不到匹配的编码，返回原始编码但去掉版本号等额外信息
        # 例如：'vp09.00.10.08' -> 'vp09'
        base_codec = codec.split('.')[0]
        return base_codec.upper()  # 转换为大写以保持一致性

    @staticmethod
    def parse_formats(formats: List[Dict], duration: float) -> List[Dict]:
        """解析并格式化 yt-dlp 输出的格式列表"""
        parser = FormatParser()
        video_info = {
            'formats': formats,
            'duration': duration,
        }
        available = parser.get_available_formats(video_info)
        return parser.get_formatted_formats(available)

    def get_formatted_formats(self, formats: List[Dict]) -> List[Dict]:
        """格式化格式信息，使其更易读"""
        if not formats:
            return []
            
        formatted_formats = []
        for f in formats:
            if not f:
                continue
                
            formatted = f.copy()
            
            # 处理文件大小
            if 'filesize' in f:
                formatted['filesize'] = self.format_filesize(f.get('filesize'))
            
            # 处理视频格式显示
            if f.get('type') == 'video':
                # 构建视频信息字符串
                video_info = []
                
                # 添加分辨率
                resolution = f.get('resolution')
                if resolution and resolution != 'unknown':
                    video_info.append(resolution)
                
                # 添加视频编码和比特率
                vcodec = f.get('vcodec')
                if vcodec:
                    vcodec = self._simplify_codec(vcodec)
                    vbr = self.format_bitrate(f.get('vbr'))
                    if vbr:  # 只在有码率时添加 @ 符号
                        video_info.append(f"{vcodec} @{vbr}")
                    else:
                        video_info.append(vcodec)
                
                # 添加文件大小
                if formatted.get('filesize') != "未知大小":
                    video_info.append(formatted['filesize'])
                
                formatted['display'] = " | ".join(video_info)
            
            # 处理音频格式显示
            else:
                audio_info = []
                
                # 添加封装格式
                protocol = f.get('protocol')
                if protocol:
                    audio_info.append(protocol)
                
                # 添加音频编码
                acodec = f.get('acodec')
                if acodec:
                    acodec = self._simplify_codec(acodec)
                    abr = self.format_bitrate(f.get('abr'))
                    if abr:  # 只在有码率时添加 @ 符号
                        audio_info.append(f"{acodec} @{abr}")
                    else:
                        audio_info.append(acodec)
                
                # 添加文件大小
                if formatted.get('filesize') != "未知大小":
                    audio_info.append(formatted['filesize'])
                
                formatted['display'] = " | ".join(audio_info)
            
            formatted_formats.append(formatted)
        
        return formatted_formats

class VideoInfoCache:
    def __init__(self, cache_dir: str = "cache"):
        """初始化缓存管理器"""
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def get_cache_path(self, url: str) -> str:
        """获取缓存文件路径"""
        # 使用URL的哈希值作为文件名
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.json")

    def save_to_cache(self, url: str, data: Dict) -> None:
        """保存数据到缓存"""
        cache_path = self.get_cache_path(url)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'data': data
            }, f, ensure_ascii=False, indent=2)

    def load_from_cache(self, url: str) -> Optional[Dict]:
        """从缓存加载数据"""
        cache_path = self.get_cache_path(url)
        if not os.path.exists(cache_path):
            return None
            
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                return cache_data.get('data')
        except Exception:
            return None

    def parse_video_info(self, url: str, json_data: Dict) -> Dict:
        """解析视频信息"""
        # 保存原始JSON数据到缓存
        self.save_to_cache(url, json_data)
        
        # 获取视频时长
        duration = json_data.get('duration', 0)
        
        # 解析格式信息
        formats = json_data.get('formats', [])
        parsed_formats = FormatParser.parse_formats(formats, duration)
        
        # 获取基本信息
        basic_info = {
            'title': json_data.get('title', ''),
            'duration': duration,
            'thumbnail': json_data.get('thumbnail', ''),
            'formats': parsed_formats
        }
        
        return basic_info

    def get_video_info(self, url: str, json_data: Dict) -> Dict:
        """获取视频信息，优先使用缓存"""
        # 尝试从缓存加载
        cached_data = self.load_from_cache(url)
        if cached_data:
            return self.parse_video_info(url, cached_data)
            
        # 如果没有缓存，解析新数据
        return self.parse_video_info(url, json_data) 