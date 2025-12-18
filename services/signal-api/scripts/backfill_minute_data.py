#!/usr/bin/env python3
"""全市场A股分钟线数据回填 - 并发优化版

注意事项:
1. Tushare分钟线API需要特殊权限，会自动降级使用AkShare
2. 分钟线数据量巨大: 5460股 × 240条/天 × N天
3. 建议先导入5-10天数据测试
"""

import os
import sys
import time
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))

async def run_async():
    from signal_api.core.quant.data.manager import DataManager, DataManagerConfig
    from signal_api.core.quant.data.checkpoint_manager import get_checkpoint_manager, SyncStatus
    import tushare as ts
    
    # 配置参数
    DAYS = 5  # 默认导入5天分钟线数据
    MAX_WORKERS = 5  # 分钟线并发数降低，避免API限流
    
    print("=" * 60)
    print(f"全市场A股分钟线数据回填 - 最近{DAYS}天")
    print("=" * 60)
    
    token = os.environ.get('TUSHARE_TOKEN')
    config = DataManagerConfig(tushare_token=token)
    dm = DataManager(config)
    cm = get_checkpoint_manager()
    
    # 获取股票列表（从checkpoint数据库读取，避免API超时）
    try:
        print("正在从checkpoint数据库读取股票列表...")
        
        import sqlite3
        today = datetime.now().strftime("%Y-%m-%d")
        
        conn = sqlite3.connect('quant_data/checkpoints.db')
        cursor = conn.execute(
            "SELECT DISTINCT symbol FROM sync_checkpoints WHERE trade_date = ? AND status = 'completed'",
            (today,)
        )
        all_symbols = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not all_symbols:
            print("错误: checkpoint数据库中没有找到已完成的股票")
            print("请先运行日线数据导入: ~/东风破/restart_backfill_fast.sh")
            return
        
        print(f"全市场A股: {len(all_symbols)} 只 (来自checkpoint)")
        
        # 过滤已完成的分钟线
        completed_today = set()
        try:
            conn = sqlite3.connect('quant_data/checkpoints.db')
            cursor = conn.execute(
                "SELECT symbol FROM sync_checkpoints WHERE trade_date = ? AND status = ? AND minute_bars > 0",
                (today, 'completed')
            )
            completed_today = set(row[0] for row in cursor.fetchall())
            conn.close()
        except:
            pass
        
        pending_symbols = [s for s in all_symbols if s not in completed_today]
        
        print(f"今日已完成分钟线: {len(completed_today)} 只")
        print(f"待回填: {len(pending_symbols)} 只")
        print(f"\n预计数据量: {len(pending_symbols)} × 240条/天 × {DAYS}天 = {len(pending_symbols)*240*DAYS:,} 条")
        print(f"预计时间: {len(pending_symbols) * 0.5 / 60 / MAX_WORKERS:.0f}-{len(pending_symbols) * 1.0 / 60 / MAX_WORKERS:.0f} 分钟\n")
        
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    completed = 0
    failed = 0
    total_bars = 0
    
    start = time.time()
    
    # 并发处理函数（直接使用AkShare，跳过Tushare）
    def process_symbol(symbol):
        try:
            import akshare as ak
            
            # 直接调用AkShare API获取分钟线数据
            try:
                # 尝试新版API
                df = ak.stock_zh_a_minute(
                    symbol=symbol,
                    period='1',  # 1分钟
                    adjust=''
                )
            except:
                # 降级到旧版API
                df = ak.stock_zh_a_hist_min_em(
                    symbol=symbol,
                    period='1',
                    adjust=''
                )
            
            if df is None or df.empty:
                bars = 0
            else:
                bars = len(df)
            
            # 更新checkpoint（保留之前的日线数据）
            existing = cm.get_progress(symbol, today)
            daily_bars = existing.daily_bars if existing else 0
            
            cm.save_progress(symbol, today, SyncStatus.COMPLETED, 
                daily_bars=daily_bars, minute_bars=bars, 
                completeness=100 if bars >= DAYS * 200 else int(bars / (DAYS * 240) * 100))
            
            return (True, bars)
        except Exception as e:
            return (False, 0)
    
    # 使用线程池并发处理
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_symbol, sym): sym for sym in pending_symbols}
        
        for i, future in enumerate(as_completed(futures)):
            symbol = futures[future]
            success, bars = future.result()
            
            if success:
                completed += 1
                total_bars += bars
            else:
                failed += 1
            
            # 进度显示
            progress = (i + 1) / len(pending_symbols) * 100
            elapsed = time.time() - start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(pending_symbols) - i - 1) / rate / 60 if rate > 0 else 0
            
            avg_bars = total_bars / completed if completed > 0 else 0
            
            print(f"\r[{i+1}/{len(pending_symbols)}] {progress:.1f}% | "
                  f"速度:{rate:.2f}股/秒 | ETA:{eta:.0f}min | "
                  f"平均:{avg_bars:.0f}条/股 | {symbol}",
                  end='', flush=True)
    
    elapsed = (time.time() - start) / 60
    
    print("\n" + "=" * 60)
    print("分钟线回填完成!")
    print(f"完成: {completed}, 失败: {failed}")
    print(f"分钟线: {total_bars:,} 条 (平均 {total_bars/completed if completed > 0 else 0:.0f} 条/股)")
    print(f"耗时: {elapsed:.1f} 分钟 ({completed/elapsed:.1f} 股/分钟)")
    print("=" * 60)
    
    # 预期数据量提示
    expected = DAYS * 240  # 每天240条
    actual_avg = total_bars / completed if completed > 0 else 0
    coverage = (actual_avg / expected * 100) if expected > 0 else 0
    
    print(f"\n📊 数据质量:")
    print(f"  预期每股: {expected} 条 ({DAYS}天 × 240条/天)")
    print(f"  实际平均: {actual_avg:.0f} 条")
    print(f"  覆盖率: {coverage:.1f}%")
    
    if coverage < 70:
        print("\n⚠️  注意: 覆盖率较低，可能原因:")
        print("  1. 非交易日或交易时间外")
        print("  2. 部分股票停牌")
        print("  3. AkShare数据源限制")

if __name__ == "__main__":
    asyncio.run(run_async())
