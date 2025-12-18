#!/usr/bin/env python3
"""数据质量检查脚本"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from signal_api.core.quant.data.duckdb_manager import DuckDBManager
import sqlite3
from datetime import datetime

print("=" * 60)
print("历史数据导入质量报告")
print("=" * 60)

# 1. 检查点数据库统计
print("\n📊 CheckPoint 数据库统计:")
print("-" * 60)

cp_db = 'quant_data/checkpoints.db'
conn = sqlite3.connect(cp_db)
today = datetime.now().strftime("%Y-%m-%d")

# 总览
cursor = conn.execute(
    "SELECT status, count(*) FROM sync_checkpoints WHERE trade_date = ? GROUP BY status",
    (today,)
)
for row in cursor:
    print(f"  状态 {row[0]:12s}: {row[1]:>5d} 只")

# 详细统计
cursor = conn.execute("""
    SELECT 
        count(*) as total,
        sum(daily_bars) as total_bars,
        avg(daily_bars) as avg_bars,
        min(daily_bars) as min_bars,
        max(daily_bars) as max_bars
    FROM sync_checkpoints 
    WHERE status='completed' AND trade_date = ?
""", (today,))

row = cursor.fetchone()
print(f"\n  总计完成: {row[0]} 只")
print(f"  总数据条目: {row[1]:,} 条")
print(f"  平均每股: {row[2]:.1f} 条")
print(f"  最少: {row[3]} 条")
print(f"  最多: {row[4]} 条")

# 质量分级
cursor = conn.execute("""
    SELECT 
        CASE 
            WHEN daily_bars >= 20 THEN '优秀 (≥20条)'
            WHEN daily_bars >= 15 THEN '良好 (15-19条)'
            WHEN daily_bars >= 10 THEN '一般 (10-14条)'
            ELSE '较差 (<10条)'
        END as quality,
        count(*) as count
    FROM sync_checkpoints 
    WHERE status='completed' AND trade_date = ?
    GROUP BY quality
    ORDER BY min(daily_bars) DESC
""", (today,))

print("\n📈 数据质量分级:")
print("-" * 60)
for row in cursor:
    pct = row[1] / 5460 * 100
    print(f"  {row[0]:15s}: {row[1]:>5d} 只 ({pct:>5.1f}%)")

conn.close()

# 2. DuckDB 数据库统计
print("\n\n💾 DuckDB 存储统计:")
print("-" * 60)

try:
    db = DuckDBManager('./quant_data/quant.duckdb')
    
    # 查询日线表
    result = db.conn.execute("""
        SELECT 
            count(DISTINCT ts_code) as stock_count,
            count(*) as total_rows,
            count(*) / count(DISTINCT ts_code) as avg_rows_per_stock
        FROM daily_data
    """).fetchone()
    
    print(f"  存储股票数: {result[0]:,} 只")
    print(f"  总数据行数: {result[1]:,} 条")
    print(f"  平均每股: {result[2]:.1f} 条")
    
    # 最新日期
    result = db.conn.execute("SELECT max(trade_date) FROM daily_data").fetchone()
    print(f"  最新日期: {result[0]}")
    
except Exception as e:
    print(f"  DuckDB检查失败: {e}")

print("\n" + "=" * 60)
print("✅ 数据导入质量检查完成!")
print("=" * 60)
