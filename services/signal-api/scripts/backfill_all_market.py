#!/usr/bin/env python3
"""全市场A股日线数据回填 (使用Tushare获取股票列表)"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

def run():
    from signal_api.core.quant.data.manager import DataManager, DataManagerConfig
    from signal_api.core.quant.data.checkpoint_manager import get_checkpoint_manager, SyncStatus
    import tushare as ts
    
    print("=" * 50)
    print("全市场A股日线数据回填")
    print("=" * 50)
    
    token = os.environ.get('TUSHARE_TOKEN')
    config = DataManagerConfig(tushare_token=token)
    dm = DataManager(config)
    cm = get_checkpoint_manager()
    
    # 使用Tushare获取全市场A股列表
    try:
        print("正在获取全市场A股列表 (Tushare)...")
        
        pro = ts.pro_api(token)
        
        # 获取上市股票
        df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,name')
        all_symbols = [code.split('.')[0] for code in df['ts_code'].tolist()]
        
        print(f"全市场A股: {len(all_symbols)} 只")
        
        # 过滤已完成的
        today = datetime.now().strftime("%Y-%m-%d")
        completed_today = set()
        try:
            import sqlite3
            conn = sqlite3.connect('quant_data/checkpoints.db')
            cursor = conn.execute(
                "SELECT symbol FROM checkpoints WHERE trade_date = ? AND status = ?",
                (today, 'completed')
            )
            completed_today = set(row[0] for row in cursor.fetchall())
            conn.close()
        except:
            pass
        
        # 过滤已完成的
        pending_symbols = [s for s in all_symbols if s not in completed_today]
        
        print(f"今日已完成: {len(completed_today)} 只")
        print(f"待回填: {len(pending_symbols)} 只")
        print(f"预计时间: {len(pending_symbols) * 0.25 / 60:.1f} 小时")
        
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    completed = 0
    failed = 0
    total_bars = 0
    
    start = time.time()
    
    for i, symbol in enumerate(pending_symbols):
        progress = (i + 1) / len(pending_symbols) * 100
        elapsed = time.time() - start
        eta = (elapsed / (i + 1)) * (len(pending_symbols) - i - 1) / 60 if i > 0 else 0
        
        print(f"[{i+1}/{len(pending_symbols)}] {progress:.1f}% ETA:{eta:.0f}min {symbol}", end='\r')
        
        try:
            # 只获取日线
            daily_df = dm.get_daily(symbol, days=30)
            bars = len(daily_df) if daily_df is not None else 0
            total_bars += bars
            
            cm.save_progress(symbol, today, SyncStatus.COMPLETED, 
                daily_bars=bars, minute_bars=0, completeness=100 if bars >= 18 else 50)
            completed += 1
        except Exception as e:
            cm.save_progress(symbol, today, SyncStatus.FAILED, error_message=str(e))
            failed += 1
        
        time.sleep(0.2)  # 控制频率
    
    elapsed = (time.time() - start) / 60
    
    print("\n" + "=" * 50)
    print("全市场回填完成!")
    print(f"完成: {completed}, 失败: {failed}")
    print(f"日线: {total_bars} 条")
    print(f"耗时: {elapsed:.1f} 分钟")
    print("=" * 50)

if __name__ == "__main__":
    run()
