"""
格式解析器测试
"""
import pytest
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFormatParser:
    """格式解析器测试"""
    
    def test_get_available_formats(self, sample_video_info):
        """测试获取可用格式"""
        from src.core.video_info.format_parser import FormatParser
        
        parser = FormatParser()
        formats = parser.get_available_formats(sample_video_info)
        
        assert len(formats) > 0
    
    def test_filter_video_formats(self, sample_video_info):
        """测试过滤视频格式"""
        from src.core.video_info.format_parser import FormatParser
        
        parser = FormatParser()
        formats = parser.get_available_formats(sample_video_info)
        
        video_formats = [f for f in formats if f.get('type') == 'video']
        assert len(video_formats) > 0
    
    def test_filter_audio_formats(self, sample_video_info):
        """测试过滤音频格式"""
        from src.core.video_info.format_parser import FormatParser
        
        parser = FormatParser()
        formats = parser.get_available_formats(sample_video_info)
        
        audio_formats = [f for f in formats if f.get('type') == 'audio']
        assert len(audio_formats) > 0
    
    def test_format_resolution(self):
        """测试格式化分辨率"""
        from src.core.video_info.format_parser import FormatParser
        
        parser = FormatParser()
        
        assert parser.format_resolution(1920, 1080) == "1920x1080"
        assert parser.format_resolution(1280, 720) == "1280x720"
    
    def test_format_filesize(self):
        """测试格式化文件大小"""
        from src.core.video_info.format_parser import FormatParser
        
        parser = FormatParser()
        
        assert parser.format_filesize(1024) == "1.00 KB"
        assert parser.format_filesize(1024 * 1024) == "1.00 MB"
        assert parser.format_filesize(1024 * 1024 * 1024) == "1.00 GB"
    
    def test_empty_video_info(self):
        """测试空视频信息"""
        from src.core.video_info.format_parser import FormatParser
        
        parser = FormatParser()
        formats = parser.get_available_formats({})
        
        assert formats == []
    
    def test_none_video_info(self):
        """测试 None 视频信息"""
        from src.core.video_info.format_parser import FormatParser
        
        parser = FormatParser()
        formats = parser.get_available_formats(None)
        
        assert formats == []


class TestCodecMapping:
    """编码映射测试"""
    
    def test_video_codec_name(self):
        """测试视频编码名称"""
        from src.core.video_info.format_parser import FormatParser
        
        parser = FormatParser()
        
        # 检查编码映射是否存在
        if parser.codec_mappings.get('video_codecs'):
            avc = parser.codec_mappings['video_codecs'].get('avc1', {})
            assert 'name' in avc or avc == {}
    
    def test_audio_codec_name(self):
        """测试音频编码名称"""
        from src.core.video_info.format_parser import FormatParser
        
        parser = FormatParser()
        
        # 检查编码映射是否存在
        if parser.codec_mappings.get('audio_codecs'):
            mp4a = parser.codec_mappings['audio_codecs'].get('mp4a', {})
            assert 'name' in mp4a or mp4a == {}

