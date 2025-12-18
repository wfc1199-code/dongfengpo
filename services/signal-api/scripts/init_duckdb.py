#!/usr/bin/env python3
"""
DuckDB 数据湖初始化脚本

用途:
- 创建 quant_data 目录结构
- 初始化 DuckDB 数据库
- 创建必要的表和索引
- 测试基本读写功能

用法:
    python scripts/init_duckdb.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def init_data_lake(data_root: str = "./quant_data"):
    """初始化数据湖目录结构"""
    print("=" * 60)
    print("DuckDB 数据湖初始化")
    print("=" * 60)
    
    root = Path(data_root)
    
    # 创建目录结构
    directories = [
        root / "market_data",      # 分钟线 Parquet 文件
        root / "daily_data",       # 日线 Parquet 文件
        root / "backup",           # 定期备份
        root / "checkpoints",      # 断点续传检查点
        root / "logs",             # 同步日志
    ]
    
    for dir_path in directories:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ 创建目录: {dir_path}")
    
    # 初始化 DuckDB
    print("\n📦 初始化 DuckDB...")
    try:
        from signal_api.core.quant.data.duckdb_manager import DuckDBManager
        
        dm = DuckDBManager(data_root=str(root))
        
        # 测试连接
        conn = dm.conn
        result = conn.execute("SELECT 1 as test").fetchone()
        print(f"  ✅ DuckDB 连接正常: {result}")
        
        dm.close()
        
    except Exception as e:
        print(f"  ⚠️ DuckDB 初始化失败: {e}")
        return False
    
    # 创建元数据文件
    meta_file = root / "metadata.json"
    if not meta_file.exists():
        import json
        metadata = {
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
            "description": "AI Quant Platform Data Lake",
            "directories": {
                "market_data": "分钟线 Parquet 文件",
                "daily_data": "日线 Parquet 文件",
                "backup": "定期备份",
                "checkpoints": "断点续传检查点",
                "logs": "同步日志",
            }
        }
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"  ✅ 创建元数据文件: {meta_file}")
    
    print("\n" + "=" * 60)
    print("✅ 数据湖初始化完成!")
    print("=" * 60)
    print(f"\n数据目录: {root.absolute()}")
    print("\n下一步:")
    print("  1. 配置 TUSHARE_TOKEN 环境变量")
    print("  2. 运行 sync_task.py 同步历史数据")
    print("  3. 设置定时任务每日同步")
    
    return True


def test_data_flow():
    """测试数据流"""
    print("\n📊 测试数据流...")
    
    try:
        from signal_api.core.quant.data.manager import DataManager, DataManagerConfig
        
        token = os.environ.get('TUSHARE_TOKEN')
        if not token:
            print("  ⚠️ TUSHARE_TOKEN 未配置，跳过数据流测试")
            return True
        
        config = DataManagerConfig(tushare_token=token)
        dm = DataManager(config)
        
        # 测试分钟线
        print("  测试分钟线获取 (000001)...")
        minute_df = dm.get_minute('000001', days=1, freq='1min')
        if minute_df is not None and len(minute_df) > 0:
            print(f"    ✅ 获取 {len(minute_df)} 条分钟线")
        else:
            print(f"    ⚠️ 无分钟线数据")
        
        # 测试日线
        print("  测试日线获取 (000001)...")
        daily_df = dm.get_daily('000001', days=30)
        if daily_df is not None and len(daily_df) > 0:
            print(f"    ✅ 获取 {len(daily_df)} 条日线")
        else:
            print(f"    ⚠️ 无日线数据")
        
        return True
        
    except Exception as e:
        print(f"  ⚠️ 数据流测试失败: {e}")
        return False


if __name__ == "__main__":
    # 切换到项目根目录
    os.chdir(project_root)
    
    # 初始化数据湖
    success = init_data_lake("./quant_data")
    
    if success:
        # 测试数据流
        test_data_flow()
