"""
异常模块测试
"""
import pytest
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestExceptions:
    """异常测试"""
    
    def test_base_exception(self):
        """测试基础异常"""
        from src.core.exceptions import YouTubeDownloaderError
        
        error = YouTubeDownloaderError("Test error", code="TEST_ERROR")
        
        assert str(error) == "[TEST_ERROR] Test error"
        assert error.message == "Test error"
        assert error.code == "TEST_ERROR"
    
    def test_exception_to_dict(self):
        """测试异常转字典"""
        from src.core.exceptions import YouTubeDownloaderError
        
        error = YouTubeDownloaderError("Test error", code="TEST_ERROR", details="extra info")
        result = error.to_dict()
        
        assert result['error_type'] == 'YouTubeDownloaderError'
        assert result['message'] == 'Test error'
        assert result['code'] == 'TEST_ERROR'
        assert result['details'] == 'extra info'
    
    def test_video_parse_error(self):
        """测试视频解析错误"""
        from src.core.exceptions import VideoParseError
        
        error = VideoParseError(url="https://example.com/video")
        
        assert error.url == "https://example.com/video"
        assert error.code == "VIDEO_PARSE_ERROR"
    
    def test_download_error(self):
        """测试下载错误"""
        from src.core.exceptions import DownloadError
        
        error = DownloadError("Download failed", url="https://example.com")
        
        assert error.url == "https://example.com"
        assert error.code == "DOWNLOAD_ERROR"
    
    def test_network_error(self):
        """测试网络错误"""
        from src.core.exceptions import NetworkError
        
        error = NetworkError("Connection refused")
        
        assert error.code == "NETWORK_ERROR"
    
    def test_cookie_error(self):
        """测试 Cookie 错误"""
        from src.core.exceptions import CookieError, CookieNotFoundError
        
        error = CookieNotFoundError(path="/path/to/cookie.txt")
        
        assert error.path == "/path/to/cookie.txt"
        assert error.code == "COOKIE_NOT_FOUND"


class TestExceptionMapper:
    """异常映射器测试"""
    
    def test_map_unavailable_error(self):
        """测试映射不可用视频错误"""
        from src.core.exceptions import ExceptionMapper, VideoUnavailableError
        
        error = ExceptionMapper.map_error("Video unavailable")
        
        assert isinstance(error, VideoUnavailableError)
    
    def test_map_private_error(self):
        """测试映射私人视频错误"""
        from src.core.exceptions import ExceptionMapper, VideoPrivateError
        
        error = ExceptionMapper.map_error("This video is private")
        
        assert isinstance(error, VideoPrivateError)
    
    def test_map_rate_limit_error(self):
        """测试映射速率限制错误"""
        from src.core.exceptions import ExceptionMapper, RateLimitError
        
        error = ExceptionMapper.map_error("HTTP Error 429: Too Many Requests")
        
        assert isinstance(error, RateLimitError)
    
    def test_map_unknown_error(self):
        """测试映射未知错误"""
        from src.core.exceptions import ExceptionMapper, DownloadError
        
        error = ExceptionMapper.map_error("Some unknown error")
        
        assert isinstance(error, DownloadError)


class TestHandleErrorsDecorator:
    """错误处理装饰器测试"""
    
    def test_handle_errors_success(self):
        """测试成功情况"""
        from src.core.exceptions import handle_errors, VideoParseError
        
        @handle_errors(VideoParseError, "解析失败")
        def parse_video():
            return {"title": "Test"}
        
        result = parse_video()
        assert result == {"title": "Test"}
    
    def test_handle_errors_exception(self):
        """测试异常情况"""
        from src.core.exceptions import handle_errors, VideoParseError
        
        @handle_errors(VideoParseError, "解析失败")
        def parse_video():
            raise ValueError("Invalid input")
        
        with pytest.raises(VideoParseError):
            parse_video()


class TestSafeExecuteDecorator:
    """安全执行装饰器测试"""
    
    def test_safe_execute_success(self):
        """测试成功情况"""
        from src.core.exceptions import safe_execute
        
        @safe_execute(default=[])
        def get_items():
            return [1, 2, 3]
        
        result = get_items()
        assert result == [1, 2, 3]
    
    def test_safe_execute_exception(self):
        """测试异常情况返回默认值"""
        from src.core.exceptions import safe_execute
        
        @safe_execute(default=[], log_error=False)
        def get_items():
            raise ValueError("Error")
        
        result = get_items()
        assert result == []

