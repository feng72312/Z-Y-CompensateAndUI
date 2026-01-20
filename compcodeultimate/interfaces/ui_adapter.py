# -*- coding: utf-8 -*-
"""
UI适配器接口
提供UI层与业务逻辑解耦的抽象接口
"""

from abc import ABC, abstractmethod
from typing import Protocol, Any, Optional, Callable, Dict, List
from dataclasses import dataclass


# ==================== 回调协议 ====================

class ProgressCallback(Protocol):
    """进度回调协议"""
    
    def __call__(self, current: int, total: int, message: str) -> None:
        """
        进度回调
        
        参数:
            current: 当前进度
            total: 总数
            message: 进度消息
        """
        ...


class LogCallback(Protocol):
    """日志回调协议"""
    
    def __call__(self, message: str, level: str = 'info') -> None:
        """
        日志回调
        
        参数:
            message: 日志消息
            level: 日志级别 (info, success, warning, error)
        """
        ...


class ResultCallback(Protocol):
    """结果回调协议"""
    
    def __call__(self, result: Any) -> None:
        """
        结果回调
        
        参数:
            result: 处理结果
        """
        ...


class ErrorCallback(Protocol):
    """错误回调协议"""
    
    def __call__(self, error: Exception, context: Optional[str] = None) -> None:
        """
        错误回调
        
        参数:
            error: 异常对象
            context: 错误上下文
        """
        ...


# ==================== UI适配器接口 ====================

@dataclass
class UICallbacks:
    """UI回调集合"""
    on_progress: Optional[ProgressCallback] = None
    on_log: Optional[LogCallback] = None
    on_result: Optional[ResultCallback] = None
    on_error: Optional[ErrorCallback] = None
    
    def log(self, message: str, level: str = 'info') -> None:
        """记录日志"""
        if self.on_log:
            self.on_log(message, level)
    
    def progress(self, current: int, total: int, message: str = '') -> None:
        """更新进度"""
        if self.on_progress:
            self.on_progress(current, total, message)
    
    def result(self, data: Any) -> None:
        """发送结果"""
        if self.on_result:
            self.on_result(data)
    
    def error(self, err: Exception, context: Optional[str] = None) -> None:
        """发送错误"""
        if self.on_error:
            self.on_error(err, context)


class UIAdapterInterface(ABC):
    """
    UI适配器抽象接口
    
    定义UI层需要实现的抽象方法，用于与业务逻辑解耦
    """
    
    @abstractmethod
    def on_progress_update(self, current: int, total: int, message: str) -> None:
        """进度更新"""
        pass
    
    @abstractmethod
    def on_log_message(self, message: str, level: str) -> None:
        """日志消息"""
        pass
    
    @abstractmethod
    def on_result_ready(self, result: Any) -> None:
        """结果就绪"""
        pass
    
    @abstractmethod
    def on_error_occurred(self, error: Exception) -> None:
        """错误发生"""
        pass
    
    @abstractmethod
    def on_status_change(self, status: str) -> None:
        """状态变化"""
        pass
    
    def get_callbacks(self) -> UICallbacks:
        """获取回调集合"""
        return UICallbacks(
            on_progress=self.on_progress_update,
            on_log=self.on_log_message,
            on_result=self.on_result_ready,
            on_error=self.on_error_occurred
        )


# ==================== 控制器基类 ====================

class BaseController:
    """
    控制器基类
    
    提供UI和服务层之间的桥接
    """
    
    def __init__(self, callbacks: Optional[UICallbacks] = None):
        """
        初始化控制器
        
        参数:
            callbacks: UI回调集合
        """
        self._callbacks = callbacks or UICallbacks()
        self._is_running = False
        self._should_cancel = False
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._is_running
    
    def cancel(self) -> None:
        """请求取消操作"""
        self._should_cancel = True
    
    def _check_cancelled(self) -> bool:
        """检查是否已取消"""
        return self._should_cancel
    
    def _reset_state(self) -> None:
        """重置状态"""
        self._is_running = False
        self._should_cancel = False
    
    def _log(self, message: str, level: str = 'info') -> None:
        """记录日志"""
        self._callbacks.log(message, level)
    
    def _progress(self, current: int, total: int, message: str = '') -> None:
        """更新进度"""
        self._callbacks.progress(current, total, message)
    
    def _result(self, data: Any) -> None:
        """发送结果"""
        self._callbacks.result(data)
    
    def _error(self, err: Exception, context: Optional[str] = None) -> None:
        """发送错误"""
        self._callbacks.error(err, context)


# ==================== 事件定义 ====================

@dataclass
class UIEvent:
    """UI事件基类"""
    event_type: str
    data: Any = None


@dataclass
class ProgressEvent(UIEvent):
    """进度事件"""
    current: int = 0
    total: int = 0
    message: str = ''
    
    def __post_init__(self):
        self.event_type = 'progress'


@dataclass
class LogEvent(UIEvent):
    """日志事件"""
    message: str = ''
    level: str = 'info'
    
    def __post_init__(self):
        self.event_type = 'log'


@dataclass
class ResultEvent(UIEvent):
    """结果事件"""
    result: Any = None
    
    def __post_init__(self):
        self.event_type = 'result'


@dataclass
class ErrorEvent(UIEvent):
    """错误事件"""
    error: Optional[Exception] = None
    context: str = ''
    
    def __post_init__(self):
        self.event_type = 'error'


# ==================== 事件队列接口 ====================

class EventQueueInterface(Protocol):
    """事件队列接口（用于跨线程通信）"""
    
    def put(self, event: UIEvent) -> None:
        """放入事件"""
        ...
    
    def get(self, timeout: Optional[float] = None) -> UIEvent:
        """获取事件"""
        ...
    
    def empty(self) -> bool:
        """队列是否为空"""
        ...
