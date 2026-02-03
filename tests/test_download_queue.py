"""
下载队列测试
"""
import pytest
import time
import threading
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.types import DownloadOptions, DownloadPriority, DownloadStatus


class TestDownloadQueue:
    """下载队列测试"""
    
    def test_add_task(self):
        """测试添加任务"""
        from src.core.download_queue import DownloadQueue
        
        queue = DownloadQueue(auto_start=False)
        
        options = DownloadOptions(
            url="https://www.youtube.com/watch?v=test",
            output_dir="/tmp/test"
        )
        
        task_id = queue.add(options)
        
        assert task_id is not None
        assert queue.get_queue_size() == 1
    
    def test_remove_task(self):
        """测试移除任务"""
        from src.core.download_queue import DownloadQueue
        
        queue = DownloadQueue(auto_start=False)
        
        options = DownloadOptions(
            url="https://www.youtube.com/watch?v=test",
            output_dir="/tmp/test"
        )
        
        task_id = queue.add(options)
        
        result = queue.remove(task_id)
        assert result is True
    
    def test_get_task(self):
        """测试获取任务"""
        from src.core.download_queue import DownloadQueue
        
        queue = DownloadQueue(auto_start=False)
        
        options = DownloadOptions(
            url="https://www.youtube.com/watch?v=test",
            output_dir="/tmp/test"
        )
        
        task_id = queue.add(options, title="Test Video")
        task = queue.get_task(task_id)
        
        assert task is not None
        assert task.url == options.url
        assert task.title == "Test Video"
    
    def test_priority_ordering(self):
        """测试优先级排序"""
        from src.core.download_queue import DownloadQueue
        
        queue = DownloadQueue(auto_start=False)
        
        # 添加不同优先级的任务
        options1 = DownloadOptions(url="https://example.com/1", output_dir="/tmp")
        options2 = DownloadOptions(url="https://example.com/2", output_dir="/tmp")
        options3 = DownloadOptions(url="https://example.com/3", output_dir="/tmp")
        
        queue.add(options1, priority=DownloadPriority.LOW)
        queue.add(options2, priority=DownloadPriority.HIGH)
        queue.add(options3, priority=DownloadPriority.NORMAL)
        
        # 高优先级任务应该先出队
        all_tasks = queue.get_all_tasks()
        assert len(all_tasks) == 3
    
    def test_pause_resume(self):
        """测试暂停和恢复"""
        from src.core.download_queue import DownloadQueue
        
        queue = DownloadQueue(auto_start=False)
        
        queue.start()
        assert queue.is_running() is True
        
        queue.pause()
        assert queue.is_paused() is True
        
        queue.resume()
        assert queue.is_paused() is False
        
        queue.stop()
        assert queue.is_running() is False
    
    def test_statistics(self):
        """测试统计信息"""
        from src.core.download_queue import DownloadQueue
        
        queue = DownloadQueue(auto_start=False)
        
        options = DownloadOptions(url="https://example.com/1", output_dir="/tmp")
        queue.add(options)
        
        stats = queue.get_statistics()
        
        assert 'total' in stats
        assert 'pending' in stats
        assert stats['total'] == 1
    
    def test_clear_all(self):
        """测试清空队列"""
        from src.core.download_queue import DownloadQueue
        
        queue = DownloadQueue(auto_start=False)
        
        options = DownloadOptions(url="https://example.com/1", output_dir="/tmp")
        queue.add(options)
        queue.add(options)
        queue.add(options)
        
        queue.clear_all()
        
        assert queue.get_queue_size() == 0
        assert len(queue.get_all_tasks()) == 0


class TestQueuedTask:
    """队列任务测试"""
    
    def test_from_options(self):
        """测试从选项创建任务"""
        from src.core.download_queue import QueuedTask
        
        options = DownloadOptions(
            url="https://example.com/video",
            output_dir="/tmp/downloads",
            video_format_id="137",
            audio_format_id="140"
        )
        
        task = QueuedTask.from_options(options)
        
        assert task.url == options.url
        assert task.output_dir == options.output_dir
        assert task.video_format_id == "137"
        assert task.audio_format_id == "140"
    
    def test_get_format_id(self):
        """测试获取格式ID"""
        from src.core.download_queue import QueuedTask
        
        task = QueuedTask(
            priority=2,
            url="https://example.com",
            output_dir="/tmp",
            video_format_id="137",
            audio_format_id="140"
        )
        
        assert task.get_format_id() == "137+140"
    
    def test_format_id_best_audio(self):
        """测试最佳音频格式ID"""
        from src.core.download_queue import QueuedTask
        
        task = QueuedTask(
            priority=2,
            url="https://example.com",
            output_dir="/tmp",
            video_format_id="137",
            audio_format_id="best"
        )
        
        assert task.get_format_id() == "137"

