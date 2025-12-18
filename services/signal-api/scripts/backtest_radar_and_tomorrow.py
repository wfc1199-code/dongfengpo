#!/usr/bin/env python3
"""
盯盘雷达 + 明日潜力 综合回测

测试两个核心策略：
1. Ignition (点火策略) - 盯盘雷达
2. Ambush (潜伏策略) - 明日潜力

使用本地持久化的分钟线数据进行回测
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import json
import pandas as pd
from datetime import datetime
from typing import List

async def run_combined_backtest():
    from signal_api.core.quant.engines.backtest import BacktestEngine, BacktestConfig
    from signal_api.core.quant.strategies.ignition import IgnitionStrategy, IgnitionConfig
    from signal_api.core.quant.strategies.ambush import AmbushStrategy, AmbushConfig
    from signal_api.core.quant.data.manager import DataManager, DataManagerConfig
    
    print("=" * 80)
    print("东风破 - 盯盘雷达 + 明日潜力 综合回测")
    print("=" * 80)
    
    # 1. 初始化数据管理器（使用本地parquet数据）
    token = os.environ.get('TUSHARE_TOKEN', 'dummy_token_for_local_data')
    dm = DataManager(DataManagerConfig(tushare_token=token))
    
    # 2. 读取有效股票列表
    valid_stocks_file = Path(__file__).parent.parent / "valid_stocks.txt"
    
    if not valid_stocks_file.exists():
        print(f"❌ 请先运行: python scripts/list_valid_stocks.py")
        return
    
    with open(valid_stocks_file, 'r') as f:
        all_valid_symbols = [line.strip() for line in f if line.strip()]
    
    if not all_valid_symbols:
        print("❌ 未找到有效的股票代码")
        return
    
    # 随机选择30只股票进行测试（更全面的回测）
    import random
    random.seed(42)
    test_symbols = random.sample(all_valid_symbols, min(30, len(all_valid_symbols)))
    
    print(f"\n📊 测试股票: {len(test_symbols)} 只 (从 {len(all_valid_symbols)} 只中随机选择)")
    print(f"   {', '.join(test_symbols[:10])}...")
    
    # 3. 配置回测引擎
    config = BacktestConfig(
        initial_capital=100_000,
        commission_rate=0.0003,
        stamp_tax_rate=0.001,
        slippage_pct=0.002,
        position_size_pct=0.2,  # 每只20%仓位
        max_positions=5,        # 最多5只
        stop_loss_pct=0.05,     # 5%止损
        take_profit_pct=0.12,   # 12%止盈
    )
    
    engine = BacktestEngine(config)
    
    # ================================================================
    # 策略1: Ignition (点火策略) - 盯盘雷达
    # ================================================================
    print(f"\n{'=' * 80}")
    print("📡 策略1: Ignition点火策略 (盯盘雷达)")
    print("=" * 80)
    print("\n📥 加载分钟数据...")
    
    minute_data_list = []
    for symbol in test_symbols:
        try:
            minute_df = dm.get_minute(symbol, days=5, freq='1min')
            if minute_df is not None and len(minute_df) >= 200:
                minute_df['symbol'] = symbol
                minute_data_list.append(minute_df)
                print(f"   ✅ {symbol}: {len(minute_df)} 条")
        except Exception as e:
            print(f"   ❌ {symbol}: {e}")
    
    if minute_data_list:
        combined_minute = pd.concat(minute_data_list, ignore_index=True)
        combined_minute = combined_minute.sort_values('datetime')
        if 'date' not in combined_minute.columns:
            combined_minute['date'] = combined_minute['datetime']
        
        print(f"\n📈 Ignition数据: {len(combined_minute):,} 条分钟线 (约 {len(combined_minute)/240:.1f} 个交易日)")
        
        # 使用默认Ignition配置
        ignition_strategy = IgnitionStrategy(IgnitionConfig())
        
        try:
            ignition_result = engine.run(ignition_strategy, combined_minute, "IGNITION_MULTI")
            
            print(f"\n🎯 Ignition点火策略回测结果:")
            print("-" * 80)
            print(f"   总收益率:     {ignition_result.total_return:.2%}")
            print(f"   年化收益率:   {ignition_result.annual_return:.2%}")
            print(f"   夏普比率:     {ignition_result.sharpe_ratio:.2f}")
            print(f"   最大回撤:     {ignition_result.max_drawdown:.2%}")
            print(f"   交易次数:     {ignition_result.total_trades} 次")
            print(f"   胜率:         {ignition_result.win_rate:.2%}")
            
        except Exception as e:
            print(f"\n❌ Ignition回测失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n⚠️  Ignition策略: 无可用分钟线数据")
    
    # ================================================================
    # 策略2: Ambush (潜伏策略) - 明日潜力
    # ================================================================
    print(f"\n{'=' * 80}")
    print("🎯 策略2: Ambush潜伏策略 (明日潜力)")
    print("=" * 80)
    print("\n📥 加载日线数据...")
    
    daily_data_list = []
    for symbol in test_symbols:
        try:
            daily_df = dm.get_daily(symbol, days=90)  # 潜伏策略需要更长的历史
            if daily_df is not None and len(daily_df) >= 30:
                daily_df['symbol'] = symbol
                daily_data_list.append(daily_df)
                print(f"   ✅ {symbol}: {len(daily_df)} 天")
        except Exception as e:
            print(f"   ❌ {symbol}: {e}")
    
    if daily_data_list:
        combined_daily = pd.concat(daily_data_list, ignore_index=True)
        
        # 标准化列名：trade_date -> datetime, vol -> volume
        rename_map = {}
        if 'trade_date' in combined_daily.columns:
            rename_map['trade_date'] = 'datetime'
        if 'vol' in combined_daily.columns:
            rename_map['vol'] = 'volume'
        if rename_map:
            combined_daily = combined_daily.rename(columns=rename_map)
        
        # 确保 datetime 是 datetime 类型
        if 'datetime' in combined_daily.columns:
            if combined_daily['datetime'].dtype == 'object' or combined_daily['datetime'].dtype == 'int64':
                combined_daily['datetime'] = pd.to_datetime(combined_daily['datetime'], format='%Y%m%d')
            combined_daily = combined_daily.sort_values('datetime')
        
        # 确保date列存在
        if 'datetime' in combined_daily.columns and 'date' not in combined_daily.columns:
            combined_daily['date'] = combined_daily['datetime']
        
        print(f"\n📈 Ambush数据: {len(combined_daily):,} 条日线 (约 {len(combined_daily)/len(daily_data_list):.0f} 天/股)")
        
        # 使用默认Ambush配置
        ambush_strategy = AmbushStrategy(AmbushConfig())
        
        try:
            ambush_result = engine.run(ambush_strategy, combined_daily, "AMBUSH_MULTI")
            
            print(f"\n🎯 Ambush潜伏策略回测结果:")
            print("-" * 80)
            print(f"   总收益率:     {ambush_result.total_return:.2%}")
            print(f"   年化收益率:   {ambush_result.annual_return:.2%}")
            print(f"   夏普比率:     {ambush_result.sharpe_ratio:.2f}")
            print(f"   最大回撤:     {ambush_result.max_drawdown:.2%}")
            print(f"   交易次数:     {ambush_result.total_trades} 次")
            print(f"   胜率:         {ambush_result.win_rate:.2%}")
            
        except Exception as e:
            print(f"\n❌ Ambush回测失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n⚠️  Ambush策略: 无可用日线数据")
    
    # ================================================================
    # 总结
    # ================================================================
    print(f"\n{'=' * 80}")
    print("📊 回测总结")
    print("=" * 80)
    
    summary = {
        'timestamp': datetime.now().isoformat(),
        'test_stocks': len(test_symbols),
        'strategies': {}
    }
    
    if minute_data_list:
        summary['strategies']['Ignition'] = {
            'total_return': f"{ignition_result.total_return:.2%}",
            'annual_return': f"{ignition_result.annual_return:.2%}",
            'sharpe_ratio': round(ignition_result.sharpe_ratio, 2),
            'max_drawdown': f"{ignition_result.max_drawdown:.2%}",
            'win_rate': f"{ignition_result.win_rate:.2%}",
            'total_trades': ignition_result.total_trades,
        }
        print(f"\n✅ Ignition (盯盘雷达):")
        print(f"   年化收益: {ignition_result.annual_return:.2%}")
        print(f"   夏普比率: {ignition_result.sharpe_ratio:.2f}")
        print(f"   胜率: {ignition_result.win_rate:.2%}")
    
    
    if daily_data_list:
        try:
            summary['strategies']['Ambush'] = {
                'total_return': f"{ambush_result.total_return:.2%}",
                'annual_return': f"{ambush_result.annual_return:.2%}",
                'sharpe_ratio': round(ambush_result.sharpe_ratio, 2),
                'max_drawdown': f"{ambush_result.max_drawdown:.2%}",
                'win_rate': f"{ambush_result.win_rate:.2%}",
                'total_trades': ambush_result.total_trades,
            }
            print(f"\n✅ Ambush (明日潜力):")
            print(f"   年化收益: {ambush_result.annual_return:.2%}")
            print(f"   夏普比率: {ambush_result.sharpe_ratio:.2f}")
            print(f"   胜率: {ambush_result.win_rate:.2%}")
        except NameError:
            print(f"\n⚠️  Ambush (明日潜力): 回测未完成")
    
    # 保存结果
    output_file = Path('combined_backtest_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 回测结果已保存到: {output_file.name}")
    print("=" * 80)

if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)
    asyncio.run(run_combined_backtest())
