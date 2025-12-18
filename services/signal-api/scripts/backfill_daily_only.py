#!/usr/bin/env python3
"""只回填日线数据（跳过分钟线，避免API限制）"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

def run():
    from signal_api.core.quant.data.manager import DataManager, DataManagerConfig
    from signal_api.core.quant.data.checkpoint_manager import get_checkpoint_manager, SyncStatus
    
    print("=" * 50)
    print("日线数据回填 (跳过分钟线)")
    print("=" * 50)
    
    token = os.environ.get('TUSHARE_TOKEN')
    config = DataManagerConfig(tushare_token=token)
    dm = DataManager(config)
    cm = get_checkpoint_manager()
    
    # 获取中证1000成分股
    try:
        import akshare as ak
        df = ak.index_stock_cons_csindex(symbol="000852")
        symbols = df['成分券代码'].tolist()[:1000]
        symbols = [str(s)[:6] for s in symbols]
        print(f"获取到 {len(symbols)} 只中证1000成分股")
    except:
        symbols = ['000001', '000002', '600000', '600036', '600519']
        print(f"使用默认 {len(symbols)} 只股票")
    
    today = datetime.now().strftime("%Y-%m-%d")
    completed = 0
    failed = 0
    total_bars = 0
    
    start = time.time()
    
    for i, symbol in enumerate(symbols):
        progress = (i + 1) / len(symbols) * 100
        print(f"[{i+1}/{len(symbols)}] {progress:.1f}% {symbol}", end='\r')
        
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
        
        time.sleep(0.3)  # 控制频率
    
    elapsed = (time.time() - start) / 60
    
    print("\n" + "=" * 50)
    print("回填完成!")
    print(f"完成: {completed}, 失败: {failed}")
    print(f"日线: {total_bars} 条")
    print(f"耗时: {elapsed:.1f} 分钟")
    print("=" * 50)

if __name__ == "__main__":
    run()
