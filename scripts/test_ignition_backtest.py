"""
点火策略回测测试脚本

使用真实的历史数据测试点火策略
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

import pandas as pd
import akshare as ak
from datetime import datetime, timedelta

# 导入策略和回测引擎（使用绝对导入）
import sys

sys.path.insert(0, project_root)

from shared.strategies.ignition import IgnitionStrategy
from backtest_engine.core.executor import BacktestEngine


def get_stock_data(code="000001", start_date="2023-01-01", end_date="2024-12-31"):
    """
    获取股票历史数据

    Args:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        DataFrame
    """
    print(f"📊 正在获取 {code} 的历史数据...")

    try:
        # 使用akshare获取A股数据
        # 平安银行: 000001
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
            adjust="qfq",  # 前复权
        )

        # 重命名列以匹配回测引擎
        df = df.rename(
            columns={
                "日期": "datetime",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
            }
        )

        # 添加code列
        df["code"] = code

        # 确保datetime是datetime类型
        df["datetime"] = pd.to_datetime(df["datetime"])

        # 只保留需要的列
        df = df[["datetime", "code", "open", "high", "low", "close", "volume"]]

        print(f"✅ 成功获取 {len(df)} 条数据")
        print(f"   时间范围: {df['datetime'].min()} 至 {df['datetime'].max()}")
        print(f"   价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")

        return df

    except Exception as e:
        print(f"❌ 获取数据失败: {e}")
        return None


def run_backtest():
    """运行回测"""
    print("=" * 60)
    print("🚀 点火策略回测测试")
    print("=" * 60)

    # 1. 获取数据
    data = get_stock_data(
        code="000001",  # 平安银行
        start_date="2024-01-01",
        end_date="2024-12-31",
    )

    if data is None or len(data) == 0:
        print("❌ 无法获取数据，测试终止")
        return

    # 2. 创建策略
    print("\n📈 创建点火策略...")
    strategy = IgnitionStrategy(volume_ratio=2.0, price_threshold=0.02)
    print(f"   策略参数: {strategy}")

    # 3. 创建回测引擎
    print("\n⚙️  初始化回测引擎...")
    engine = BacktestEngine(
        strategy=strategy,
        initial_cash=100000.0,
        commission=0.0003,  # 0.03%
        slippage=0.001,  # 0.1%
    )
    print(f"   初始资金: ¥{engine.account.initial_cash:,.2f}")
    print(f"   手续费率: {engine.account.commission_rate * 100:.2f}%")
    print(f"   滑点率: {engine.account.slippage * 100:.2f}%")

    # 4. 运行回测
    print("\n🏃 开始回测...")
    result = engine.run(data)

    # 5. 打印结果
    print("\n" + "=" * 60)
    print("📊 回测结果")
    print("=" * 60)

    print(f"\n💰 资金情况:")
    print(f"   初始资金: ¥{result['initial_cash']:,.2f}")
    print(f"   最终资产: ¥{result['final_value']:,.2f}")
    print(f"   绝对收益: ¥{result['final_value'] - result['initial_cash']:,.2f}")

    print(f"\n📈 收益指标:")
    print(f"   总收益率: {result['total_return'] * 100:.2f}%")
    print(f"   年化收益率: {result['annual_return'] * 100:.2f}%")

    print(f"\n📝 交易统计:")
    print(f"   交易次数: {result['total_trades']}")

    if result["trades"]:
        print(f"\n🔍 交易记录（前5笔）:")
        for i, trade in enumerate(result["trades"][:5]):
            action = trade["side"]
            print(
                f"   {i+1}. {trade['datetime'].strftime('%Y-%m-%d')} "
                f"{action:4s} "
                f"{trade['quantity']:>6d}股 @ ¥{trade['price']:.2f}"
            )
            if "profit" in trade:
                print(f"      盈亏: ¥{trade['profit']:,.2f}")

    if result["equity_curve"]:
        print(f"\n📉 净值曲线（采样10个点）:")
        equity_df = pd.DataFrame(result["equity_curve"])
        sample_idx = [int(i * len(equity_df) / 9) for i in range(10)]
        for idx in sample_idx:
            if idx < len(equity_df):
                row = equity_df.iloc[idx]
                date = pd.to_datetime(row["datetime"]).strftime("%Y-%m-%d")
                value = row["total_value"]
                ret = (value / result["initial_cash"] - 1) * 100
                print(f"   {date}: ¥{value:,.2f} ({ret:+.2f}%)")

    print("\n" + "=" * 60)
    print("✅ 回测完成！")
    print("=" * 60)

    return result


if __name__ == "__main__":
    run_backtest()
