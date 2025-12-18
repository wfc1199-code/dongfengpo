#!/usr/bin/env python3
"""
数据状态查看器 - 让数据可视化、透明化

用法：
    python scripts/inspect_data.py              # 查看整体状态
    python scripts/inspect_data.py --detail     # 详细报告
    python scripts/inspect_data.py --symbol 000001  # 查看特定股票
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from datetime import datetime, timedelta
import pandas as pd

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def get_checkpoint_stats():
    """获取checkpoint数据库统计"""
    print_header("📊 Checkpoint 数据库状态")
    
    db_path = 'quant_data/checkpoints.db'
    if not os.path.exists(db_path):
        print("  ❌ 数据库不存在")
        return
    
    conn = sqlite3.connect(db_path)
    
    # 文件大小
    size_mb = os.path.getsize(db_path) / 1024 / 1024
    print(f"  数据库大小: {size_mb:.2f} MB")
    
    # 总记录数
    cursor = conn.execute("SELECT count(*) FROM sync_checkpoints")
    total = cursor.fetchone()[0]
    print(f"  总记录数: {total:,}")
    
    # 按日期统计
    print("\n  📅 按日期统计:")
    cursor = conn.execute("""
        SELECT trade_date, count(*) as cnt, 
               sum(daily_bars) as daily, sum(minute_bars) as minute
        FROM sync_checkpoints 
        GROUP BY trade_date 
        ORDER BY trade_date DESC 
        LIMIT 5
    """)
    
    print(f"  {'日期':12s} {'股票数':>8s} {'日线条数':>12s} {'分钟线条数':>12s}")
    print(f"  {'-'*12} {'-'*8} {'-'*12} {'-'*12}")
    for row in cursor:
        print(f"  {row[0]:12s} {row[1]:8,d} {row[2] or 0:12,d} {row[3] or 0:12,d}")
    
    # 数据质量
    print("\n  📈 数据质量分析:")
    today = datetime.now().strftime("%Y-%m-%d")
    
    cursor = conn.execute(f"""
        SELECT 
            count(*) as total,
            sum(CASE WHEN daily_bars >= 40 THEN 1 ELSE 0 END) as good_daily,
            sum(CASE WHEN minute_bars >= 1000 THEN 1 ELSE 0 END) as good_minute
        FROM sync_checkpoints 
        WHERE trade_date = '{today}'
    """)
    row = cursor.fetchone()
    
    if row and row[0] > 0:
        print(f"  日线数据充足 (≥40条): {row[1]:,} / {row[0]:,} ({row[1]/row[0]*100:.1f}%)")
        print(f"  分钟线充足 (≥1000条): {row[2]:,} / {row[0]:,} ({row[2]/row[0]*100:.1f}%)")
    
    conn.close()

def get_data_freshness():
    """检查数据新鲜度"""
    print_header("🕐 数据新鲜度")
    
    db_path = 'quant_data/checkpoints.db'
    if not os.path.exists(db_path):
        return
    
    conn = sqlite3.connect(db_path)
    
    cursor = conn.execute("SELECT max(trade_date), max(updated_at) FROM sync_checkpoints")
    row = cursor.fetchone()
    
    if row[0]:
        latest_date = row[0]
        latest_update = row[1]
        
        print(f"  最新数据日期: {latest_date}")
        print(f"  最后更新时间: {latest_update}")
        
        # 计算距今天数
        try:
            latest = datetime.strptime(latest_date, "%Y-%m-%d")
            today = datetime.now()
            days_old = (today - latest).days
            
            if days_old == 0:
                print(f"  状态: ✅ 数据是最新的")
            elif days_old <= 3:
                print(f"  状态: ⚠️  数据有 {days_old} 天旧（周末/节假日正常）")
            else:
                print(f"  状态: ❌ 数据已过期 {days_old} 天，需要更新")
        except:
            pass
    
    conn.close()

def get_storage_info():
    """存储空间信息"""
    print_header("💾 存储空间")
    
    data_dir = Path('quant_data')
    if not data_dir.exists():
        print("  ❌ 数据目录不存在")
        return
    
    total_size = 0
    file_list = []
    
    for file_path in data_dir.rglob('*'):
        if file_path.is_file():
            size = file_path.stat().st_size
            total_size += size
            file_list.append((file_path.name, size / 1024 / 1024))
    
    print(f"  数据目录: {data_dir.absolute()}")
    print(f"  总大小: {total_size / 1024 / 1024:.2f} MB")
    print(f"\n  主要文件:")
    
    # 按大小排序
    file_list.sort(key=lambda x: x[1], reverse=True)
    for name, size in file_list[:10]:
        print(f"    {name:40s} {size:8.2f} MB")

def inspect_symbol(symbol):
    """检查特定股票的数据"""
    print_header(f"🔍 股票 {symbol} 数据详情")
    
    db_path = 'quant_data/checkpoints.db'
    if not os.path.exists(db_path):
        print("  ❌ 数据库不存在")
        return
    
    conn = sqlite3.connect(db_path)
    
    cursor = conn.execute("""
        SELECT trade_date, status, daily_bars, minute_bars, completeness, updated_at
        FROM sync_checkpoints 
        WHERE symbol = ?
        ORDER BY trade_date DESC
        LIMIT 10
    """, (symbol,))
    
    rows = cursor.fetchall()
    
    if not rows:
        print(f"  ❌ 未找到股票 {symbol} 的数据")
        return
    
    print(f"\n  {'日期':12s} {'状态':12s} {'日线':>8s} {'分钟':>8s} {'完整度':>8s} {'更新时间':20s}")
    print(f"  {'-'*12} {'-'*12} {'-'*8} {'-'*8} {'-'*8} {'-'*20}")
    
    for row in rows:
        print(f"  {row[0]:12s} {row[1]:12s} {row[2] or 0:8d} {row[3] or 0:8d} {row[4] or 0:7.1f}% {row[5][:19]}")
    
    conn.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='数据状态查看器')
    parser.add_argument('--detail', action='store_true', help='显示详细信息')
    parser.add_argument('--symbol', type=str, help='查看特定股票')
    
    args = parser.parse_args()
    
    print("\n" + "🔍 东风破 - 数据状态检查器".center(70, "="))
    print(f"  检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.symbol:
        inspect_symbol(args.symbol)
    else:
        get_checkpoint_stats()
        get_data_freshness()
        get_storage_info()
        
        if args.detail:
            print_header("📋 更多信息")
            print("  使用 --symbol <代码> 查看特定股票详情")
            print("  数据文件位置: quant_data/")
            print("  checkpoint DB: quant_data/checkpoints.db")
    
    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    main()
