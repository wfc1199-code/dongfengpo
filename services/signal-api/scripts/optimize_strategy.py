#!/usr/bin/env python3
"""
策略参数优化 - 自动寻找最佳参数组合

功能：
1. 网格搜索多组参数
2. Walk-Forward验证（避免过拟合）
3. 按样本外表现排序
4. 保存最优参数

用法：
    python scripts/optimize_strategy.py
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from datetime import datetime
import pandas as pd
import json

async def optimize_ambush():
    from signal_api.core.quant.engines.backtest import BacktestEngine, BacktestConfig
    from signal_api.core.quant.strategies.ambush import AmbushStrategy, AmbushConfig
    
    print("=" * 70)
    print("东风破 - Ambush策略参数优化")
    print("=" * 70)
    
    # 1. 加载测试数据
    import sqlite3
    conn = sqlite3.connect('quant_data/checkpoints.db')
    cursor = conn.execute("""
        SELECT symbol FROM sync_checkpoints 
        WHERE daily_bars >= 40
        ORDER BY daily_bars DESC
        LIMIT 10
    """)
    test_symbols = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print(f"\n📊 测试股票: {len(test_symbols)} 只")
    print(f"   {', '.join(test_symbols[:5])}...")
    
    # 2. 合并多只股票数据（增加样本量）
    all_data = []
    
    for symbol in test_symbols:
        parquet_file = f"quant_data/quant.duckdb/daily_data/{symbol}.SZ.parquet"
        if not os.path.exists(parquet_file):
            parquet_file = f"quant_data/quant.duckdb/daily_data/{symbol}.SH.parquet"
        
        if os.path.exists(parquet_file):
            try:
                df = pd.read_parquet(parquet_file)
                df['symbol'] = symbol
                all_data.append(df)
            except:
                pass
    
    if not all_data:
        print("❌ 没有找到可用数据")
        return
    
    # 合并数据
    combined_data = pd.concat(all_data, ignore_index=True)
    combined_data = combined_data.sort_values('trade_date')
    combined_data['datetime'] = pd.to_datetime(combined_data['trade_date'])
    
    if 'vol' in combined_data.columns:
        combined_data = combined_data.rename(columns={'vol': 'volume'})
    
    print(f"\n📈 总数据量: {len(combined_data)} 条")
    print(f"   日期范围: {combined_data['trade_date'].min()} - {combined_data['trade_date'].max()}")
    
    # 3. 配置回测引擎
    config = BacktestConfig(
        initial_capital=100_000,
        commission_rate=0.0003,
        stamp_tax_rate=0.001,
        slippage_pct=0.001,
        position_size_pct=0.2,  # 每笔20%
        max_positions=5,
        stop_loss_pct=0.05,
        take_profit_pct=0.15,
    )
    
    engine = BacktestEngine(config)
    
    # 4. 定义参数网格
    param_grid = {
        'lookback_days': [20, 30],  # 回看天数
        'min_confidence': [0.55, 0.65],  # 最小置信度
        'volume_ratio_min': [1.2, 1.5],  # 量比下限
        'volume_ratio_max': [4.0, 5.0],  # 量比上限
        'max_intraday_range': [0.05, 0.06],  # 最大日内波动
        'washout_days': [3, 5],  # 洗盘天数
        'min_washout_pct': [0.03, 0.05],  # 最小洗盘幅度
        'max_washout_pct': [0.12, 0.15],  # 最大洗盘幅度
    }
    
    total_combinations = 1
    for v in param_grid.values():
        total_combinations *= len(v)
    
    print(f"\n🔍 参数优化:")
    print(f"   参数组合数: {total_combinations}")
    print(f"   训练集比例: 70%")
    print(f"   测试集比例: 30%")
    print(f"\n开始搜索最优参数...")
    print("-" * 70)
    
    # 5. 运行参数扫描
    try:
        results = engine.run_parameter_sweep(
            strategy_class=AmbushStrategy,
            config_class=AmbushConfig,
            data=combined_data,
            param_grid=param_grid,
            symbol="MULTI",
            use_walk_forward=True,
            train_ratio=0.7
        )
        
        if not results:
            print("\n❌ 参数优化失败：所有参数组合都未生成交易")
            print("\n💡 建议:")
            print("   1. 数据可能不符合Ambush策略特征")
            print("   2. 参数范围可能需要进一步放宽")
            print("   3. 考虑测试其他策略")
            return
        
        print(f"\n✅ 完成! 找到 {len(results)} 组有效参数")
        print("\n" + "=" * 70)
        print("🏆 Top 5 最优参数 (按样本外夏普排序)")
        print("=" * 70)
        
        for i, result in enumerate(results[:5], 1):
            print(f"\n#{i}. 参数组合:")
            for k, v in result.parameters.items():
                print(f"   {k:25s}: {v}")
            
            print(f"\n   训练集表现:")
            print(f"   - 总收益: {result.total_return:.2%}")
            print(f"   - 夏普比率: {result.sharpe_ratio:.2f}")
            print(f"   - 交易次数: {result.total_trades}")
            print(f"   - 胜率: {result.win_rate:.2%}")
            print(f"   - 最大回撤: {result.max_drawdown:.2%}")
        
        # 6. 保存最优参数
        best_result = results[0]
        
        output = {
            'timestamp': datetime.now().isoformat(),
            'strategy': 'AmbushStrategy',
            'best_parameters': best_result.parameters,
            'best_performance': {
                'total_return': best_result.total_return,
                'sharpe_ratio': best_result.sharpe_ratio,
                'max_drawdown': best_result.max_drawdown,
                'win_rate': best_result.win_rate,
                'total_trades': best_result.total_trades,
            },
            'top_5': [
                {
                    'parameters': r.parameters,
                    'sharpe': r.sharpe_ratio,
                    'return': r.total_return,
                }
                for r in results[:5]
            ]
        }
        
        with open('optimal_parameters.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 70)
        print("💾 最优参数已保存到 optimal_parameters.json")
        print("=" * 70)
        
        # 7. 生成建议的策略配置
        print("\n📋 建议使用的策略配置:")
        print("-" * 70)
        print("from signal_api.core.quant.strategies.ambush import AmbushConfig")
        print("")
        print("config = AmbushConfig(")
        for k, v in best_result.parameters.items():
            print(f"    {k}={v},")
        print(")")
        print("-" * 70)
        
    except Exception as e:
        print(f"\n❌ 优化过程出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)
    asyncio.run(optimize_ambush())
