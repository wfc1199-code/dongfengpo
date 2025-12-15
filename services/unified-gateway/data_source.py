"""
数据源模块 - 复用backend的数据获取功能
"""

import sys
from pathlib import Path

# 添加backend路径以便导入
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# 现在可以直接导入
from core.data_sources import TencentDataSource

__all__ = ['TencentDataSource']
