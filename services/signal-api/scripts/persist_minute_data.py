#!/usr/bin/env python3
"""
强制持久化分钟线数据

从checkpoint读取已下载的分钟线数据，触发查询以持久化到parquet文件
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import time
from datetime import datetime

async def persist_minute_data():
    from signal_api.core.quant.data.manager import DataManager, DataManagerConfig
    import sqlite3
    import akshare as ak
    
    print("=" * 70)
    print("东风破 - 强制持久化分钟线数据")
    print("=" * 70)
    
    # 1. 从checkpoint获取有分钟线数据的股票
    conn = sqlite3.connect('quant_data/checkpoints.db')
    cursor = conn.execute("""
        SELECT symbol, minute_bars 
        FROM sync_checkpoints 
        WHERE minute_bars > 0
        ORDER BY minute_bars DESC
    """)
    
    stocks = list(cursor.fetchall())
    conn.close()
    
    print(f"\n📊 找到 {len(stocks)} 只股票有分钟线数据")
    
    total_bars = sum(s[1] for s in stocks)
    print(f"   总数据量: {total_bars:,} 条")
    print(f"   平均每股: {total_bars/len(stocks):.0f} 条")
    
    # 2. 初始化DuckDB管理器
    from signal_api.core.quant.data.duckdb_manager import DuckDBManager
    import pandas as pd
    
    duckdb_mgr = DuckDBManager()
    
    print(f"\n💾 开始持久化...")
    print(f"   目标目录: quant_data/quant.duckdb/market_data/")
    print("-" * 70)
    
    start_time = time.time()
    success = 0
    failed = 0
    skipped = 0
    
    for i, (symbol, minute_bars) in enumerate(stocks):
        try:
            # 直接使用经过验证的AkShare API
            df = ak.stock_zh_a_hist_min_em(
                symbol=symbol,
                period='1',
                adjust=''
            )
            
            if df is None or df.empty:
                skipped += 1
                continue
            
            # 标准化列名
            df = df.rename(columns={
                '时间': 'datetime',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
            })
            
            # 确保必要列存在
            required = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            for col in required:
                if col not in df.columns:
                    df[col] = 0
            
            if 'amount' not in df.columns:
                df['amount'] = df['close'] * df['volume']
            
            # 转换symbol格式（需要加上市场后缀）
            if symbol.startswith('6'):
                ts_code = f"{symbol}.SH"
            else:
                ts_code = f"{symbol}.SZ"
            
            # 保存到parquet
            duckdb_mgr.save_minute_data(ts_code, df[required + ['amount']])
            
            success += 1
            
            # 进度显示
            progress = (i + 1) / len(stocks) * 100
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(stocks) - i - 1) / rate / 60 if rate > 0 else 0
            
            print(f"\r[{i+1}/{len(stocks)}] {progress:.1f}% | "
                  f"速度:{rate:.1f}股/秒 | ETA:{eta:.0f}min | "
                  f"✅ {success} ❌ {failed} ⚠️ {skipped} | {symbol}",
                  end='', flush=True)
            
            # 避免过快请求
            await asyncio.sleep(0.05)
            
        except Exception as e:
            failed += 1
            if i % 10 == 0:  # 每10个显示一次错误
                print(f"\n   ❌ {symbol}: {str(e)[:50]}")
    
    elapsed = (time.time() - start_time) / 60
    
    print("\n" + "=" * 70)
    print("📈 持久化完成!")
    print("=" * 70)
    print(f"\n统计:")
    print(f"  成功: {success} 只")
    print(f"  失败: {failed} 只")
    print(f"  跳过: {skipped} 只")
    print(f"  耗时: {elapsed:.1f} 分钟 ({success/elapsed:.1f} 股/分钟)")
    
    # 验证结果
    print(f"\n🔍 验证持久化结果...")
    market_data_dir = Path('quant_data/quant.duckdb/market_data')
    if market_data_dir.exists():
        parquet_files = list(market_data_dir.glob('*.parquet'))
        print(f"   Parquet文件数: {len(parquet_files)}")
        
        if parquet_files:
            # 检查几个文件
            total_size = sum(f.stat().st_size for f in parquet_files)
            print(f"   总大小: {total_size/1024/1024:.2f} MB")
            print(f"\n   示例文件:")
            for f in parquet_files[:5]:
                size_kb = f.stat().st_size / 1024
                print(f"     {f.name:20s} {size_kb:8.1f} KB")
    
    print("\n" + "=" * 70)
    print("✅ 所有分钟线数据已持久化到parquet文件!")
    print("=" * 70)

if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)
    asyncio.run(persist_minute_data())
