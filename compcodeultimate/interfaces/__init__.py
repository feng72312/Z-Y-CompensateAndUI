# -*- coding: utf-8 -*-
"""
接口层
提供 CLI 和 UI 适配器接口
"""

from .ui_adapter import (
    UICallbacks,
    UIAdapterInterface,
    BaseController,
    ProgressCallback,
    LogCallback,
    ResultCallback,
    ErrorCallback,
    UIEvent,
    ProgressEvent,
    LogEvent,
    ResultEvent,
    ErrorEvent
)

from .cli import main as cli_main, create_parser

__all__ = [
    # UI Adapter
    'UICallbacks',
    'UIAdapterInterface',
    'BaseController',
    'ProgressCallback',
    'LogCallback',
    'ResultCallback',
    'ErrorCallback',
    # Events
    'UIEvent',
    'ProgressEvent',
    'LogEvent',
    'ResultEvent',
    'ErrorEvent',
    # CLI
    'cli_main',
    'create_parser'
]
