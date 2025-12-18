#!/usr/bin/env python3
"""
Ignition策略分钟线回测 + 参数优化

使用5天分钟线数据测试点火策略
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import json
import pandas as pd
from datetime import datetime

async def optimize_ignition_minute():
    from signal_api.core.quant.engines.backtest import BacktestEngine, BacktestConfig
    from signal_api.core.quant.strategies.ignition import IgnitionStrategy, IgnitionConfig
    from signal_api.core.quant.data.manager import DataManager, DataManagerConfig
    
    print("=" * 70)
    print("东风破 - Ignition策略分钟线回测")
    print("=" * 70)
    
    
    # 1. 初始化数据管理器（优先使用本地parquet数据）
    # 注意：现在不需要真正的Tushare token，因为我们优先从本地parquet读取
    token = os.environ.get('TUSHARE_TOKEN', 'dummy_token_for_local_data')
    dm = DataManager(DataManagerConfig(tushare_token=token))
    
    
    # 2. 选择测试股票 - 从持久化数据中读取
    valid_stocks_file = Path(__file__).parent.parent / "valid_stocks.txt"
    
    if not valid_stocks_file.exists():
        print(f"❌ 请先运行: python scripts/list_valid_stocks.py")
        return
    
    with open(valid_stocks_file, 'r') as f:
        all_valid_symbols = [line.strip() for line in f if line.strip()]
    
    if not all_valid_symbols:
        print("❌ 未找到有效的股票代码")
        return
    
    # 随机选择10只股票进行测试（更有代表性）
    import random
    random.seed(42)  # 固定随机种子，结果可复现
    test_symbols = random.sample(all_valid_symbols, min(10, len(all_valid_symbols)))
    
    print(f"\n📊 测试股票: {len(test_symbols)} 只 (从 {len(all_valid_symbols)} 只中随机选择)")
    print(f"   {', '.join(test_symbols[:5])}...")
    
    # 3. 合并分钟数据
    print(f"\n📥 加载分钟数据...")
    all_data = []
    
    for symbol in test_symbols:
        try:
            minute_df = dm.get_minute(symbol, days=5, freq='1min')
            
            if minute_df is not None and len(minute_df) >= 500:
                minute_df['symbol'] = symbol
                all_data.append(minute_df)
                print(f"   ✅ {symbol}: {len(minute_df)} 条")
            else:
                print(f"   ⚠️  {symbol}: 数据不足")
        except Exception as e:
            print(f"   ❌ {symbol}: {e}")
    
    if not all_data:
        print("\n❌ 没有加载到可用的分钟数据")
        return
    
    # 合并数据
    combined_data = pd.concat(all_data, ignore_index=True)
    combined_data = combined_data.sort_values('datetime')
    
    # 确保必要的列
    if 'date' not in combined_data.columns:
        combined_data['date'] = combined_data['datetime']
    
    print(f"\n📈 总数据量: {len(combined_data):,} 条 (约 {len(combined_data)/240:.1f} 个交易日)")
    
    # 4. 配置回测引擎
    config = BacktestConfig(
        initial_capital=100_000,
        commission_rate=0.0003,
        stamp_tax_rate=0.001,
        slippage_pct=0.002,  # 分钟线滑点稍高
        position_size_pct=0.3,
        max_positions=3,
        stop_loss_pct=0.03,  # 3%止损
        take_profit_pct=0.08,  # 8%止盈
    )
    
    engine = BacktestEngine(config)
    
    # 5. 参数优化
    print(f"\n🔍 Ignition策略参数优化...")
    print("-" * 70)
    
    param_grid = {
        'minute_volume_ratio_min': [2.5, 3.0, 3.5],  # 分时量比最小值
        'cumulative_volume_ratio_min': [1.2, 1.5],  # 累计量比最小值
        'breakout_threshold': [0.015, 0.02, 0.025],  # 突破幅度
        'min_confidence': [0.6, 0.7],  # 最小置信度
    }
    
    total_combinations = 1
    for v in param_grid.values():
        total_combinations *= len(v)
    
    print(f"   参数组合数: {total_combinations}")
    print(f"   训练/测试比例: 70/30")
    
    try:
        results = engine.run_parameter_sweep(
            strategy_class=IgnitionStrategy,
            config_class=IgnitionConfig,
            data=combined_data,
            param_grid=param_grid,
            symbol="MULTI_MINUTE",
            use_walk_forward=True,
            train_ratio=0.7
        )
        
        if not results:
            print("\n❌ 所有参数组合都未产生交易")
            print("   可能原因: 数据特征不符合Ignition策略条件")
            return
        
        print(f"\n✅ 完成! 找到 {len(results)} 组有效参数")
        print("\n" + "=" * 70)
        print("🏆 Top 5 最优参数 (按样本外夏普排序)")
        print("=" * 70)
        
        for i, result in enumerate(results[:5], 1):
            print(f"\n#{i}. 参数组合:")
            for k, v in result.parameters.items():
                if not k.startswith('_'):
                    print(f"   {k:30s}: {v}")
            
            print(f"\n   训练集表现:")
            print(f"   - 总收益: {result.total_return:.2%}")
            print(f"   - 年化收益: {result.annual_return:.2%}")
            print(f"   - 夏普比率: {result.sharpe_ratio:.2f}")
            print(f"   - 交易次数: {result.total_trades}")
            print(f"   - 胜率: {result.win_rate:.2%}")
            print(f"   - 最大回撤: {result.max_drawdown:.2%}")
        
        # 6. 保存最优参数
        best_result = results[0]
        best_params = {k: v for k, v in best_result.parameters.items() if not k.startswith('_')}
        
        output = {
            'timestamp': datetime.now().isoformat(),
            'strategy': 'IgnitionStrategy',
            'data_type': 'minute',
            'best_parameters': best_params,
            'best_performance': {
                'total_return': best_result.total_return,
                'annual_return': best_result.annual_return,
                'sharpe_ratio': best_result.sharpe_ratio,
                'max_drawdown': best_result.max_drawdown,
                'win_rate': best_result.win_rate,
                'total_trades': best_result.total_trades,
            },
            'top_5': [
                {
                    'parameters': {k: v for k, v in r.parameters.items() if not k.startswith('_')},
                    'sharpe': r.sharpe_ratio,
                    'return': r.total_return,
                }
                for r in results[:5]
            ]
        }
        
        with open('ignition_optimal_params.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 70)
        print("💾 最优参数已保存到 ignition_optimal_params.json")
        print("=" * 70)
        
        print("\n📋 建议使用的策略配置:")
        print("-" * 70)
        print("from signal_api.core.quant.strategies.ignition import IgnitionConfig")
        print("")
        print("config = IgnitionConfig(")
        for k, v in best_params.items():
            print(f"    {k}={v},")
        print(")")
        print("-" * 70)
        
        # 7. 用最优参数测试单股
        print("\n" + "=" * 70)
        print("📊 使用最优参数测试单股表现")
        print("=" * 70)
        
        strategy = IgnitionStrategy(IgnitionConfig(**best_params))
        
        for symbol in test_symbols[:5]:
            try:
                minute_df = dm.get_minute(symbol, days=5, freq='1min')
                
                if minute_df is None or len(minute_df) < 500:
                    continue
                
                if 'date' not in minute_df.columns:
                    minute_df['date'] = minute_df['datetime']
                
                result = engine.run(strategy, minute_df, symbol)
                
                print(f"\n{symbol}:")
                print(f"  收益: {result.total_return:.2%}")
                print(f"  夏普: {result.sharpe_ratio:.2f}")
                print(f"  交易: {result.total_trades}次")
                print(f"  胜率: {result.win_rate:.2%}")
                
            except Exception as e:
                print(f"\n{symbol}: 测试失败 - {e}")
        
    except Exception as e:
        print(f"\n❌ 优化失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)
    asyncio.run(optimize_ignition_minute())
