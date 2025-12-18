#!/usr/bin/env python3
"""
检查分钟线数据持久化进度

快速查看已持久化的分钟线数据数量和状态
"""

import os
from pathlib import Path

def check_persist_progress():
    print("=" * 70)
    print("分钟线数据持久化进度检查")
    print("=" * 70)
    
    # 1. 检查checkpoint中的总数
    import sqlite3
    conn = sqlite3.connect('quant_data/checkpoints.db')
    cursor = conn.execute("""
        SELECT COUNT(*), SUM(minute_bars) 
        FROM sync_checkpoints 
        WHERE minute_bars > 0
    """)
    total_stocks, total_bars = cursor.fetchone()
    conn.close()
    
    print(f"\n📊 Checkpoint数据库:")
    print(f"   应有分钟数据的股票: {total_stocks:,} 只")
    print(f"   分钟线总条数: {total_bars:,} 条")
    
    # 2. 检查已持久化的parquet文件
    market_data_dir = Path('quant_data/market_data')  # 修正路径
    
    if not market_data_dir.exists():
        print(f"\n❌ market_data目录不存在")
        return
    
    parquet_files = list(market_data_dir.glob('*.parquet'))
    
    if not parquet_files:
        print(f"\n⚠️  未找到parquet文件，持久化可能还未开始")
        return
    
    print(f"\n💾 已持久化的Parquet文件:")
    print(f"   文件数量: {len(parquet_files):,} 个")
    
    # 计算总大小
    total_size = sum(f.stat().st_size for f in parquet_files)
    print(f"   总大小: {total_size/1024/1024:.2f} MB")
    
    # 计算进度
    progress = len(parquet_files) / total_stocks * 100 if total_stocks > 0 else 0
    print(f"   进度: {progress:.1f}% ({len(parquet_files)}/{total_stocks})")
    
    # 估算剩余时间（基于0.3股/秒）
    remaining = total_stocks - len(parquet_files)
    if remaining > 0:
        eta_minutes = remaining / (0.3 * 60)
        eta_hours = eta_minutes / 60
        print(f"   预计剩余时间: {eta_hours:.1f} 小时")
    
    # 显示部分文件
    print(f"\n   最新的5个文件:")
    sorted_files = sorted(parquet_files, key=lambda f: f.stat().st_mtime, reverse=True)
    for f in sorted_files[:5]:
        size_kb = f.stat().st_size / 1024
        import time
        mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(f.stat().st_mtime))
        print(f"     {f.name:20s} {size_kb:8.1f} KB  {mtime}")
    
    # 3. 状态判断
    print(f"\n📈 状态:")
    if progress >= 99:
        print(f"   ✅ 持久化已完成!")
    elif progress > 50:
        print(f"   🔄 持久化进行中（过半）")
    elif progress > 0:
        print(f"   🔄 持久化进行中")
    else:
        print(f"   ⏳ 持久化未开始或刚开始")
    
    print("=" * 70)

if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)
    check_persist_progress()
