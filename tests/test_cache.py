"""
缓存模块测试
"""
import pytest
import time
import os
import tempfile
from pathlib import Path


class TestMemoryCache:
    """内存缓存测试"""
    
    def test_set_and_get(self):
        """测试设置和获取"""
        from src.core.cache import MemoryCache
        
        cache = MemoryCache(max_size=10)
        cache.set('key1', 'value1')
        
        assert cache.get('key1') == 'value1'
    
    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        from src.core.cache import MemoryCache
        
        cache = MemoryCache()
        assert cache.get('nonexistent') is None
    
    def test_delete(self):
        """测试删除"""
        from src.core.cache import MemoryCache
        
        cache = MemoryCache()
        cache.set('key1', 'value1')
        
        assert cache.delete('key1') is True
        assert cache.get('key1') is None
        assert cache.delete('nonexistent') is False
    
    def test_exists(self):
        """测试存在检查"""
        from src.core.cache import MemoryCache
        
        cache = MemoryCache()
        cache.set('key1', 'value1')
        
        assert cache.exists('key1') is True
        assert cache.exists('key2') is False
    
    def test_max_size(self):
        """测试最大容量限制"""
        from src.core.cache import MemoryCache
        
        cache = MemoryCache(max_size=3)
        
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.set('key3', 'value3')
        cache.set('key4', 'value4')  # 应该驱逐 key1
        
        assert cache.size() == 3
        assert cache.get('key1') is None  # key1 应该被驱逐
        assert cache.get('key4') == 'value4'
    
    def test_ttl_expiration(self):
        """测试过期"""
        from src.core.cache import MemoryCache
        
        cache = MemoryCache()
        cache.set('key1', 'value1', ttl_seconds=1)
        
        assert cache.get('key1') == 'value1'
        
        time.sleep(1.5)
        
        assert cache.get('key1') is None  # 应该过期
    
    def test_clear(self):
        """测试清空"""
        from src.core.cache import MemoryCache
        
        cache = MemoryCache()
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        
        cache.clear()
        
        assert cache.size() == 0


class TestSQLiteCache:
    """SQLite 缓存测试"""
    
    def test_set_and_get(self, temp_dir):
        """测试设置和获取"""
        from src.core.cache import SQLiteCache
        
        db_path = os.path.join(temp_dir, 'test_cache.db')
        cache = SQLiteCache(db_path=db_path)
        
        cache.set('key1', {'data': 'test'})
        result = cache.get('key1')
        
        assert result == {'data': 'test'}
    
    def test_persistence(self, temp_dir):
        """测试持久化"""
        from src.core.cache import SQLiteCache
        
        db_path = os.path.join(temp_dir, 'test_cache.db')
        
        # 第一个实例
        cache1 = SQLiteCache(db_path=db_path)
        cache1.set('key1', 'value1')
        
        # 第二个实例（模拟重启）
        cache2 = SQLiteCache(db_path=db_path)
        assert cache2.get('key1') == 'value1'
    
    def test_expiration(self, temp_dir):
        """测试过期"""
        from src.core.cache import SQLiteCache
        
        db_path = os.path.join(temp_dir, 'test_cache.db')
        cache = SQLiteCache(db_path=db_path)
        
        cache.set('key1', 'value1', ttl_seconds=1)
        assert cache.get('key1') == 'value1'
        
        time.sleep(1.5)
        assert cache.get('key1') is None
    
    def test_cleanup_expired(self, temp_dir):
        """测试清理过期项"""
        from src.core.cache import SQLiteCache
        
        db_path = os.path.join(temp_dir, 'test_cache.db')
        cache = SQLiteCache(db_path=db_path)
        
        cache.set('key1', 'value1', ttl_seconds=1)
        cache.set('key2', 'value2')  # 无过期
        
        time.sleep(1.5)
        
        count = cache.cleanup_expired()
        assert count == 1
        assert cache.get('key2') == 'value2'


class TestTwoLevelCache:
    """双层缓存测试"""
    
    def test_memory_hit(self, temp_dir):
        """测试内存命中"""
        from src.core.cache import TwoLevelCache
        
        cache = TwoLevelCache(name="test")
        cache.set('key1', 'value1')
        
        # 应该从内存获取
        assert cache.get('key1') == 'value1'
    
    def test_sqlite_fallback(self, temp_dir):
        """测试 SQLite 回退"""
        from src.core.cache import TwoLevelCache
        
        cache = TwoLevelCache(name="test")
        cache.set('key1', 'value1')
        
        # 清空内存缓存
        cache._memory.clear()
        
        # 应该从 SQLite 获取并回填内存
        assert cache.get('key1') == 'value1'
        assert cache._memory.exists('key1')
    
    def test_get_or_set(self, temp_dir):
        """测试 get_or_set"""
        from src.core.cache import TwoLevelCache
        
        cache = TwoLevelCache(name="test")
        
        call_count = 0
        
        def factory():
            nonlocal call_count
            call_count += 1
            return 'computed_value'
        
        # 第一次调用应该执行 factory
        result1 = cache.get_or_set('key1', factory)
        assert result1 == 'computed_value'
        assert call_count == 1
        
        # 第二次调用应该使用缓存
        result2 = cache.get_or_set('key1', factory)
        assert result2 == 'computed_value'
        assert call_count == 1  # factory 不应该再次调用

