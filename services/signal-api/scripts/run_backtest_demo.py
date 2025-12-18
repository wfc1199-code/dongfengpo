#!/usr/bin/env python3
"""
策略回测演示

用途：
1. 测试 Ambush 和 Ignition 策略
2. 使用最近60天数据
3. 生成性能报告

用法：
    python scripts/run_backtest_demo.py
    python scripts/run_backtest_demo.py --strategy ambush  # 只测Ambush
    python scripts/run_backtest_demo.py --strategy ignition  # 只测Ignition
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from datetime import datetime, timedelta
import pandas as pd

async def run_backtest_demo():
    from signal_api.core.quant.engines.backtest import BacktestEngine, BacktestConfig
    from signal_api.core.quant.strategies.ambush import AmbushStrategy, AmbushConfig
    from signal_api.core.quant.strategies.ignition import IgnitionStrategy, IgnitionConfig
    from signal_api.core.quant.data.manager import DataManager, DataManagerConfig
    
    print("=" * 70)
    print("东风破 - 策略回测演示")
    print("=" * 70)
    
    # 2. 选择测试股票（从checkpoint选几只有完整数据的）
    import sqlite3
    conn = sqlite3.connect('quant_data/checkpoints.db')
    cursor = conn.execute("""
        SELECT symbol FROM sync_checkpoints 
        WHERE daily_bars >= 40 AND minute_bars >= 1000
        ORDER BY daily_bars DESC
        LIMIT 5
    """)
    test_symbols = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not test_symbols:
        print("❌ 没有找到符合条件的测试股票")
        print("   需要: 日线≥40条 且 分钟线≥1000条")
        return
    
    print(f"\n📊 测试股票: {', '.join(test_symbols)}")
    
    # 3. 配置回测引擎
    config = BacktestConfig(
        initial_capital=100_000,      # 10万初始资金
        commission_rate=0.0003,        # 万三佣金
        stamp_tax_rate=0.001,          # 千一印花税
        slippage_pct=0.001,            # 0.1%滑点
        position_size_pct=0.3,         # 每笔30%仓位
        max_positions=3,               # 最多3个持仓
        stop_loss_pct=0.05,            # 5%止损
        take_profit_pct=0.15,          # 15%止盈
    )
    
    engine = BacktestEngine(config)
    
    # 4. 测试 Ambush 策略
    print("\n" + "-" * 70)
    print("🎯 策略1: Ambush (潜伏策略)")
    print("-" * 70)
    
    ambush_results = []
    
    for symbol in test_symbols[:3]:  # 测试3只股票
        print(f"\n测试 {symbol}...")
        
        # 直接从parquet文件读取数据
        parquet_file = f"quant_data/quant.duckdb/daily_data/{symbol}.SZ.parquet"
        if not os.path.exists(parquet_file):
            parquet_file = f"quant_data/quant.duckdb/daily_data/{symbol}.SH.parquet"
        
        if not os.path.exists(parquet_file):
            print(f"  跳过 {symbol}: 文件不存在")
            continue
        
        try:
            daily_data = pd.read_parquet(parquet_file)
            
            if len(daily_data) < 40:
                print(f"  跳过 {symbol}: 数据不足 ({len(daily_data)}条)")
                continue
            
            # 准备数据格式
            daily_data = daily_data.sort_values('trade_date')
            daily_data['datetime'] = pd.to_datetime(daily_data['trade_date'])
            
            # 确保必要的列存在
            if 'vol' in daily_data.columns:
                daily_data = daily_data.rename(columns={'vol': 'volume'})
            
            # 运行回测
            strategy = AmbushStrategy(AmbushConfig())
            result = engine.run(strategy, daily_data[-60:], symbol)  # 最近60天
            
            ambush_results.append(result)
            
            print(f"  总收益: {result.total_return:.2%}")
            print(f"  夏普比率: {result.sharpe_ratio:.2f}")
            print(f"  最大回撤: {result.max_drawdown:.2%}")
            print(f"  交易次数: {result.total_trades}")
            print(f"  胜率: {result.win_rate:.2%}")
        
        except Exception as e:
            print(f"  回测失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 5. 测试 Ignition 策略（暂时跳过，分钟数据需要特殊处理）
    print("\n" + "-" * 70)
    print("🔥 策略2: Ignition (点火策略) - 暂时跳过")
    print("   提示: 分钟线数据量大，需要专门的聚合脚本")
    print("-" * 70)
    
    ignition_results = []
    
    # 6. 汇总报告
    print("\n" + "=" * 70)
    print("📈 回测汇总")
    print("=" * 70)
    
    if ambush_results:
        avg_return = sum(r.total_return for r in ambush_results) / len(ambush_results)
        avg_sharpe = sum(r.sharpe_ratio for r in ambush_results) / len(ambush_results)
        
        print(f"\nAmbush 策略 ({len(ambush_results)} 只股票):")
        print(f"  平均收益: {avg_return:.2%}")
        print(f"  平均夏普: {avg_sharpe:.2f}")
    
    if ignition_results:
        avg_return = sum(r.total_return for r in ignition_results) / len(ignition_results)
        avg_sharpe = sum(r.sharpe_ratio for r in ignition_results) / len(ignition_results)
        
        print(f"\nIgnition 策略 ({len(ignition_results)} 只股票):")
        print(f"  平均收益: {avg_return:.2%}")
        print(f"  平均夏普: {avg_sharpe:.2f}")
    
    print("\n" + "=" * 70)
    print("✅ 回测演示完成!")
    print("=" * 70)
    
    # 7. 保存详细结果
    if ambush_results or ignition_results:
        print("\n💾 保存详细结果到 backtest_results.json...")
        import json
        
        results_data = {
            'timestamp': datetime.now().isoformat(),
            'config': config.to_dict() if hasattr(config, 'to_dict') else str(config),
            'ambush': [r.to_dict() for r in ambush_results],
            'ignition': [r.to_dict() for r in ignition_results]
        }
        
        with open('backtest_results.json', 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        print("✅ 结果已保存")

if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)
    asyncio.run(run_backtest_demo())
