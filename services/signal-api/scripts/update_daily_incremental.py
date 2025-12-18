#!/usr/bin/env python3
"""
增量数据更新脚本 - 只更新新上市股票或缺失数据

对比完整回填的优势：
- 只下载增量数据，速度快（1-2分钟 vs 40分钟）
- 适合每日维护
- 降低API调用次数
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

async def run_async():
    from signal_api.core.quant.data.manager import DataManager, DataManagerConfig
    from signal_api.core.quant.data.checkpoint_manager import get_checkpoint_manager, SyncStatus
    import tushare as ts
    import sqlite3
    
    print("=" * 60)
    print("增量数据更新")
    print("=" * 60)
    
    token = os.environ.get('TUSHARE_TOKEN')
    config = DataManagerConfig(tushare_token=token)
    dm = DataManager(config)
    cm = get_checkpoint_manager()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 1. 获取所有股票列表
    try:
        pro = ts.pro_api(token)
        df = pro.stock_basic(exchange='', list_status='L', fields='ts_code')
        all_symbols = set(code.split('.')[0] for code in df['ts_code'].tolist())
        print(f"✅ 全市场A股: {len(all_symbols)} 只")
    except Exception as e:
        print(f"❌ 获取股票列表失败: {e}")
        return
    
    # 2. 获取已有股票列表
    try:
        conn = sqlite3.connect('quant_data/checkpoints.db')
        cursor = conn.execute(
            "SELECT DISTINCT symbol FROM sync_checkpoints WHERE trade_date = ?",
            (today,)
        )
        existing = set(row[0] for row in cursor.fetchall())
        conn.close()
        print(f"✅ 已有数据: {len(existing)} 只")
    except:
        existing = set()
    
    # 3. 找出新增股票
    new_symbols = all_symbols - existing
    
    if not new_symbols:
        print("\n🎉 没有新增股票，数据已是最新！")
        return
    
    print(f"\n📥 需要更新: {len(new_symbols)} 只新股")
    print(f"预计时间: {len(new_symbols) * 0.5 / 60:.1f} 分钟\n")
    
    # 4. 下载新股数据
    completed = 0
    failed = 0
    start = time.time()
    
    def process_symbol(symbol):
        try:
            # 日线
            daily_df = dm.get_daily(symbol, days=60)
            daily_bars = len(daily_df) if daily_df is not None else 0
            
            # 分钟线
            minute_df = dm.get_minute(symbol, days=5, freq='1min')
            minute_bars = len(minute_df) if minute_df is not None else 0
            
            cm.save_progress(symbol, today, SyncStatus.COMPLETED,
                daily_bars=daily_bars, minute_bars=minute_bars,
                completeness=100 if daily_bars >= 40 else 50)
            
            return (True, daily_bars, minute_bars)
        except Exception as e:
            cm.save_progress(symbol, today, SyncStatus.FAILED, error_message=str(e))
            return (False, 0, 0)
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_symbol, sym): sym for sym in new_symbols}
        
        for i, future in enumerate(as_completed(futures)):
            symbol = futures[future]
            success, daily, minute = future.result()
            
            if success:
                completed += 1
            else:
                failed += 1
            
            progress = (i + 1) / len(new_symbols) * 100
            elapsed = time.time() - start
            eta = (len(new_symbols) - i - 1) * (elapsed / (i + 1)) / 60 if i > 0 else 0
            
            print(f"\r[{i+1}/{len(new_symbols)}] {progress:.1f}% | "
                  f"ETA:{eta:.0f}min | {symbol}", end='', flush=True)
    
    elapsed = (time.time() - start) / 60
    
    print(f"\n\n{'='*60}")
    print(f"✅ 增量更新完成!")
    print(f"   完成: {completed}, 失败: {failed}")
    print(f"   耗时: {elapsed:.1f} 分钟")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_async())
