# -*- coding: utf-8 -*-
"""
命令行入口点
允许使用 python -m compcodeultimate 运行
"""

import sys
from .interfaces.cli import main

if __name__ == '__main__':
    sys.exit(main())
