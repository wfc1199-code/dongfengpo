#!/usr/bin/env python3
"""
使用最优参数运行回测

从 optimal_parameters.json 加载最优参数并运行完整回测
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import json
import pandas as pd
from datetime import datetime

async def run_optimized_backtest():
    from signal_api.core.quant.engines.backtest import BacktestEngine, BacktestConfig
    from signal_api.core.quant.strategies.ambush import AmbushStrategy, AmbushConfig
    
    print("=" * 70)
    print("东风破 - 最优参数回测")
    print("=" * 70)
    
    # 1. 加载最优参数
    try:
        with open('optimal_parameters.json', 'r', encoding='utf-8') as f:
            optimal = json.load(f)
        
        best_params = optimal['best_parameters']
        # 移除内部参数
        best_params = {k: v for k, v in best_params.items() if not k.startswith('_')}
        
        print("\n📋 加载最优参数:")
        for k, v in best_params.items():
            print(f"   {k:25s}: {v}")
    
    except FileNotFoundError:
        print("\n❌ 未找到 optimal_parameters.json")
        print("   请先运行: python scripts/optimize_strategy.py")
        return
    
    # 2. 加载测试数据
    import sqlite3
    conn = sqlite3.connect('quant_data/checkpoints.db')
    cursor = conn.execute("""
        SELECT symbol FROM sync_checkpoints 
        WHERE daily_bars >= 40
        ORDER BY daily_bars DESC
        LIMIT 20
    """)
    test_symbols = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print(f"\n📊 回测股票池: {len(test_symbols)} 只")
    
    # 3. 加载所有股票数据
    all_results = []
    
    config = BacktestConfig(
        initial_capital=100_000,
        commission_rate=0.0003,
        stamp_tax_rate=0.001,
        slippage_pct=0.001,
        position_size_pct=0.2,
        max_positions=5,
        stop_loss_pct=0.05,
        take_profit_pct=0.15,
    )
    
    engine = BacktestEngine(config)
    strategy = AmbushStrategy(AmbushConfig(**best_params))
    
    print("\n" + "-" * 70)
    print("开始回测...")
    print("-" * 70)
    
    tested = 0
    skipped = 0
    
    for symbol in test_symbols:
        parquet_file = f"quant_data/quant.duckdb/daily_data/{symbol}.SZ.parquet"
        if not os.path.exists(parquet_file):
            parquet_file = f"quant_data/quant.duckdb/daily_data/{symbol}.SH.parquet"
        
        if not os.path.exists(parquet_file):
            skipped += 1
            continue
        
        try:
            df = pd.read_parquet(parquet_file)
            
            if len(df) < 30:
                skipped += 1
                continue
            
            df = df.sort_values('trade_date')
            df['datetime'] = pd.to_datetime(df['trade_date'])
            
            if 'vol' in df.columns:
                df = df.rename(columns={'vol': 'volume'})
            
            # 运行回测
            result = engine.run(strategy, df, symbol)
            
            if result.total_trades > 0:
                all_results.append(result)
                tested += 1
                
                print(f"✅ {symbol:8s} | 收益:{result.total_return:7.2%} | "
                      f"夏普:{result.sharpe_ratio:5.2f} | "
                      f"交易:{result.total_trades:2d}次 | "
                      f"胜率:{result.win_rate:5.1f}%")
            else:
                tested += 1
                print(f"⚠️  {symbol:8s} | 无交易信号")
        
        except Exception as e:
            skipped += 1
            print(f"❌ {symbol:8s} | 错误: {str(e)[:40]}")
    
    # 4. 汇总报告
    print("\n" + "=" * 70)
    print("📈 回测汇总报告")
    print("=" * 70)
    
    print(f"\n股票统计:")
    print(f"  测试成功: {tested} 只")
    print(f"  跳过/失败: {skipped} 只")
    print(f"  产生信号: {len(all_results)} 只")
    
    if not all_results:
        print("\n⚠️  没有股票产生交易信号")
        return
    
    # 计算综合指标
    total_return = sum(r.total_return for r in all_results) / len(all_results)
    avg_sharpe = sum(r.sharpe_ratio for r in all_results) / len(all_results)
    avg_drawdown = sum(r.max_drawdown for r in all_results) / len(all_results)
    total_trades = sum(r.total_trades for r in all_results)
    avg_win_rate = sum(r.win_rate for r in all_results) / len(all_results)
    
    winning_stocks = [r for r in all_results if r.total_return > 0]
    
    print(f"\n整体表现:")
    print(f"  平均收益率: {total_return:.2%}")
    print(f"  平均夏普比率: {avg_sharpe:.2f}")
    print(f"  平均最大回撤: {avg_drawdown:.2%}")
    print(f"  总交易次数: {total_trades}")
    print(f"  平均胜率: {avg_win_rate:.2%}")
    print(f"  盈利股票数: {len(winning_stocks)}/{len(all_results)} ({len(winning_stocks)/len(all_results)*100:.1f}%)")
    
    # Top 5 最佳表现
    print(f"\n🏆 Top 5 最佳表现:")
    sorted_results = sorted(all_results, key=lambda x: x.total_return, reverse=True)
    
    for i, r in enumerate(sorted_results[:5], 1):
        print(f"  {i}. {r.strategy_name:8s} | "
              f"收益:{r.total_return:7.2%} | "
              f"夏普:{r.sharpe_ratio:5.2f} | "
              f"回撤:{r.max_drawdown:6.2%} | "
              f"胜率:{r.win_rate:5.1f}%")
    
    # 保存详细结果
    print(f"\n💾 保存详细结果...")
    
    results_data = {
        'timestamp': datetime.now().isoformat(),
        'strategy': 'AmbushStrategy_Optimized',
        'parameters': best_params,
        'summary': {
            'stocks_tested': tested,
            'stocks_with_signals': len(all_results),
            'avg_return': total_return,
            'avg_sharpe': avg_sharpe,
            'avg_drawdown': avg_drawdown,
            'total_trades': total_trades,
            'avg_win_rate': avg_win_rate,
            'profitable_ratio': len(winning_stocks) / len(all_results) if all_results else 0
        },
        'detailed_results': [
            {
                'symbol': r.strategy_name,
                'return': r.total_return,
                'sharpe': r.sharpe_ratio,
                'drawdown': r.max_drawdown,
                'trades': r.total_trades,
                'win_rate': r.win_rate,
            }
            for r in sorted_results
        ]
    }
    
    with open('optimized_backtest_results.json', 'w', encoding='utf-8') as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 结果已保存到 optimized_backtest_results.json")
    
    print("\n" + "=" * 70)
    print("✅ 回测完成!")
    print("=" * 70)

if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)
    asyncio.run(run_optimized_backtest())
