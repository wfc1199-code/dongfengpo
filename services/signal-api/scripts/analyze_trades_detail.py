#!/usr/bin/env python3
"""
Backtest Trade Detail Analyzer

This script runs the strategy backtests and extracts granular details for every trade:
- Symbol and Date
- Buy/Sell prices and timestamps
- Return per trade
- Daily breakdown
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

async def run_detailed_analysis():
    from signal_api.core.quant.engines.backtest import BacktestEngine, BacktestConfig, Trade
    from signal_api.core.quant.strategies.ignition import IgnitionStrategy, IgnitionConfig
    from signal_api.core.quant.strategies.ambush import AmbushStrategy, AmbushConfig
    from signal_api.core.quant.data.manager import DataManager, DataManagerConfig
    
    print("=" * 80)
    print("东风破 - 策略回测细节深度分析报告")
    print("=" * 80)
    
    # 1. Init Data Manager (use local data)
    token = os.environ.get('TUSHARE_TOKEN', 'dummy_token_for_local_data')
    dm = DataManager(DataManagerConfig(tushare_token=token))
    
    # 2. Load Valid Stocks
    valid_stocks_file = Path(__file__).parent.parent / "valid_stocks.txt"
    if not valid_stocks_file.exists():
        print("❌ Please run: python scripts/list_valid_stocks.py first")
        return
        
    with open(valid_stocks_file, 'r') as f:
        all_valid_symbols = [line.strip() for line in f if line.strip()]
        
    # Pick 20 stocks for a focused but detailed report
    import random
    random.seed(42)
    test_symbols = random.sample(all_valid_symbols, min(20, len(all_valid_symbols)))
    
    # Engine Settings
    config = BacktestConfig(
        initial_capital=100_000,
        position_size_pct=0.2,
        max_positions=5,
        stop_loss_pct=0.03,
        take_profit_pct=0.08,
    )
    engine = BacktestEngine(config)
    
    # ANALYSIS: Strategy 1 - Ignition (Radar)
    print("\n🔍 正在分析: Ignition点火策略 (盯盘雷达)...")
    
    all_minute_data = []
    for symbol in test_symbols:
        df = dm.get_minute(symbol, days=5)
        if df is not None and not df.empty:
            df['symbol'] = symbol
            all_minute_data.append(df)
            
    if all_minute_data:
        combined_minute = pd.concat(all_minute_data).sort_values('datetime')
        if 'date' not in combined_minute.columns: combined_minute['date'] = combined_minute['datetime']
        
        ignition_strategy = IgnitionStrategy(IgnitionConfig())
        ignition_result = engine.run(ignition_strategy, combined_minute, "MULTI_STOCK")
        
        print(f"\n📡 [Ignition点火策略] 交易细节:")
        print("-" * 60)
        
        if not ignition_result.trades:
            print("⚠️ 本次测试周期内未触发交易信号")
        else:
            # Group by day
            trades_by_day = defaultdict(list)
            for t in ignition_result.trades:
                day_str = t.entry_time.strftime("%Y-%m-%d")
                trades_by_day[day_str].append(t)
                
            for day in sorted(trades_by_day.keys()):
                print(f"\n📅 日期: {day}")
                for i, t in enumerate(trades_by_day[day], 1):
                    # Find stock name if possible (omitted for speed in this script)
                    print(f"  [{i}] 股票代码: {t.symbol}:")
                    print(f"      📍 买入: {t.entry_time.strftime('%H:%M:%S')} @ ¥{t.entry_price:.2f}")
                    print(f"      📍 卖出: {t.exit_time.strftime('%H:%M:%S')} @ ¥{t.exit_price:.2f}")
                    print(f"      📈 收益: {t.pnl_pct*100:+.2f}% (¥{t.pnl:+.2f})")
                    print(f"      📝 原因: {t.exit_reason}")
                    
    # ANALYSIS: Strategy 2 - Ambush (Tomorrow Potential)
    print("\n\n🔍 正在分析: Ambush潜伏策略 (明日潜力)...")
    
    all_daily_data = []
    for symbol in test_symbols:
        df = dm.get_daily(symbol, days=90)
        if df is not None and not df.empty:
            # Normalize columns for engine
            rename_map = {'trade_date': 'datetime', 'vol': 'volume'}
            df = df.rename(columns={k:v for k,v in rename_map.items() if k in df.columns})
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'], format='%Y%m%d')
                df['date'] = df['datetime']
            df['symbol'] = symbol
            all_daily_data.append(df)
            
    if all_daily_data:
        combined_daily = pd.concat(all_daily_data).sort_values('datetime')
        
        ambush_strategy = AmbushStrategy(AmbushConfig())
        ambush_result = engine.run(ambush_strategy, combined_daily, "AMBUSH")
        
        print(f"\n🎯 [Ambush潜伏策略] 交易细节:")
        print("-" * 60)
        
        if not ambush_result.trades:
            print("⚠️ 本次测试周期内未触发交易信号")
        else:
            for i, t in enumerate(sorted(ambush_result.trades, key=lambda x: x.entry_time), 1):
                day_str = t.entry_time.strftime("%Y-%m-%d")
                print(f"  [{i}] {t.symbol} ({day_str}):")
                print(f"      📍 买入日期: {t.entry_time.strftime('%Y-%m-%d')} @ ¥{t.entry_price:.2f}")
                print(f"      📍 卖出日期: {t.exit_time.strftime('%Y-%m-%d')} @ ¥{t.exit_price:.2f}")
                print(f"      📈 收益: {t.pnl_pct*100:+.2f}% (¥{t.pnl:+.2f})")
                print(f"      📝 原因: {t.exit_reason}")

    print("\n" + "=" * 80)
    print("✅ 分析报告生成完成")
    print("=" * 80)

if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)
    asyncio.run(run_detailed_analysis())
