"""
事件总线测试
"""
import pytest
import time
import threading


class TestEventBus:
    """事件总线测试"""
    
    def test_subscribe_and_publish(self):
        """测试订阅和发布"""
        from src.core.event_bus import EventBus, Events
        
        bus = EventBus()
        bus.clear()  # 清空之前的订阅
        
        received = []
        
        def handler(event):
            received.append(event.data)
        
        bus.subscribe('test:event', handler)
        bus.publish('test:event', {'message': 'hello'})
        
        assert len(received) == 1
        assert received[0] == {'message': 'hello'}
    
    def test_unsubscribe(self):
        """测试取消订阅"""
        from src.core.event_bus import EventBus
        
        bus = EventBus()
        bus.clear()
        
        received = []
        
        def handler(event):
            received.append(event.data)
        
        unsubscribe = bus.subscribe('test:event', handler)
        
        bus.publish('test:event', {'msg': '1'})
        assert len(received) == 1
        
        unsubscribe()
        
        bus.publish('test:event', {'msg': '2'})
        assert len(received) == 1  # 应该还是 1
    
    def test_multiple_subscribers(self):
        """测试多个订阅者"""
        from src.core.event_bus import EventBus
        
        bus = EventBus()
        bus.clear()
        
        received1 = []
        received2 = []
        
        def handler1(event):
            received1.append(event.data)
        
        def handler2(event):
            received2.append(event.data)
        
        bus.subscribe('test:event', handler1)
        bus.subscribe('test:event', handler2)
        
        bus.publish('test:event', {'msg': 'test'})
        
        assert len(received1) == 1
        assert len(received2) == 1
    
    def test_emit(self):
        """测试 emit 快捷方法"""
        from src.core.event_bus import EventBus
        
        bus = EventBus()
        bus.clear()
        
        received = []
        
        def handler(event):
            received.append(event.data)
        
        bus.subscribe('test:event', handler)
        bus.emit('test:event', key1='value1', key2='value2')
        
        assert len(received) == 1
        assert received[0]['key1'] == 'value1'
        assert received[0]['key2'] == 'value2'
    
    def test_on_decorator(self):
        """测试装饰器订阅"""
        from src.core.event_bus import EventBus
        
        bus = EventBus()
        bus.clear()
        
        received = []
        
        @bus.on('test:event')
        def handler(event):
            received.append(event.data)
        
        bus.emit('test:event', msg='hello')
        
        assert len(received) == 1
    
    def test_once(self):
        """测试一次性订阅"""
        from src.core.event_bus import EventBus
        
        bus = EventBus()
        bus.clear()
        
        received = []
        
        def handler(event):
            received.append(event.data)
        
        bus.once('test:event', handler)
        
        bus.publish('test:event', {'msg': '1'})
        bus.publish('test:event', {'msg': '2'})
        
        assert len(received) == 1  # 只应该收到一次
    
    def test_subscriber_count(self):
        """测试订阅者计数"""
        from src.core.event_bus import EventBus
        
        bus = EventBus()
        bus.clear()
        
        def handler(event):
            pass
        
        bus.subscribe('event1', handler)
        bus.subscribe('event1', handler)
        bus.subscribe('event2', handler)
        
        assert bus.get_subscriber_count('event1') == 2
        assert bus.get_subscriber_count('event2') == 1
        assert bus.get_subscriber_count() == 3
    
    def test_unsubscribe_all(self):
        """测试取消所有订阅"""
        from src.core.event_bus import EventBus
        
        bus = EventBus()
        bus.clear()
        
        def handler(event):
            pass
        
        bus.subscribe('event1', handler)
        bus.subscribe('event2', handler)
        
        bus.unsubscribe_all('event1')
        
        assert bus.get_subscriber_count('event1') == 0
        assert bus.get_subscriber_count('event2') == 1

