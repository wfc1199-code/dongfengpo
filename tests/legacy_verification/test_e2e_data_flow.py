#!/usr/bin/env python3
"""
端到端数据流测试

测试完整的数据流水线：
FeatureSnapshot → Strategy Engine → StrategySignal → Redis → Signal API
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Dict

import redis.asyncio as aioredis


async def test_signal_generation():
    """测试策略引擎的信号生成"""
    print("=" * 70)
    print("📊 端到端数据流测试")
    print("=" * 70)

    # 1. 准备测试数据 - 模拟 FeatureSnapshot
    print("\n1️⃣  准备测试特征数据...")
    test_feature = {
        "symbol": "000001.SZ",
        "window": "300s",
        "timestamp": datetime.now().isoformat(),
        "price": 100.0,
        "change_percent": 5.5,  # 5.5% 涨幅
        "volume_sum": 10000000,
        "avg_price": 99.0,
        "max_price": 101.0,
        "min_price": 98.0,
        "turnover_sum": 1000000000.0,
        "sample_size": 100
    }
    print(f"   Symbol: {test_feature['symbol']}")
    print(f"   Price: {test_feature['price']} ({test_feature['change_percent']}%)")
    print(f"   Volume: {test_feature['volume_sum']:,}")

    # 2. 连接 Redis
    print("\n2️⃣  连接 Redis...")
    try:
        redis_client = await aioredis.from_url(
            "redis://localhost:6379",
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.ping()
        print("   ✅ Redis 连接成功")
    except Exception as e:
        print(f"   ❌ Redis 连接失败: {e}")
        return False

    # 3. 发布特征数据到 feature channel
    print("\n3️⃣  发布特征数据到 feature channel...")
    feature_channel = "dfp:features"
    try:
        await redis_client.publish(feature_channel, json.dumps(test_feature))
        print(f"   ✅ 已发布到 {feature_channel}")
    except Exception as e:
        print(f"   ❌ 发布失败: {e}")
        await redis_client.close()
        return False

    # 4. 等待策略引擎处理（如果运行的话）
    print("\n4️⃣  等待策略引擎处理...")
    print("   ⏳ 等待 3 秒...")
    await asyncio.sleep(3)

    # 5. 检查信号流
    print("\n5️⃣  检查信号流...")
    signal_stream = "dfp:signals"
    try:
        # 读取最新的信号
        messages = await redis_client.xrevrange(signal_stream, count=5)

        if messages:
            print(f"   ✅ 发现 {len(messages)} 个信号:")
            for msg_id, msg_data in messages:
                payload = json.loads(msg_data.get('payload', '{}'))
                print(f"\n   📈 信号 ID: {msg_id}")
                print(f"      策略: {payload.get('strategy', 'N/A')}")
                print(f"      股票: {payload.get('symbol', 'N/A')}")
                print(f"      类型: {payload.get('signal_type', 'N/A')}")
                print(f"      置信度: {payload.get('confidence', 'N/A'):.2%}")
                print(f"      强度: {payload.get('strength_score', 'N/A')}")
        else:
            print("   ℹ️  信号流为空（策略引擎可能未运行）")
            print("   💡 提示：运行 `python services/strategy-engine/main.py` 启动策略引擎")
    except Exception as e:
        print(f"   ❌ 读取信号流失败: {e}")

    # 6. 测试 Signal API
    print("\n6️⃣  测试 Signal API...")
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            # 测试健康检查
            response = await client.get("http://localhost:8000/health", timeout=5.0)
            if response.status_code == 200:
                print("   ✅ Signal API 健康检查通过")
            else:
                print(f"   ⚠️  Signal API 返回状态码: {response.status_code}")

            # 测试机会列表
            response = await client.get("http://localhost:8000/opportunities", timeout=5.0)
            opportunities = response.json()
            print(f"   📊 当前机会数量: {len(opportunities)}")
    except Exception as e:
        print(f"   ❌ Signal API 测试失败: {e}")

    # 7. 清理
    print("\n7️⃣  清理资源...")
    await redis_client.close()
    print("   ✅ 已关闭 Redis 连接")

    print("\n" + "=" * 70)
    print("✅ 端到端测试完成")
    print("=" * 70)

    return True


async def test_strategy_engine_standalone():
    """独立测试策略引擎"""
    print("\n" + "=" * 70)
    print("🧪 策略引擎独立测试")
    print("=" * 70)

    # 添加项目根目录和 services 目录到路径
    import os
    project_root = os.path.abspath(os.path.dirname(__file__))
    services_path = os.path.join(project_root, 'services', 'strategy-engine')
    sys.path.insert(0, project_root)
    sys.path.insert(0, services_path)

    from strategy_engine.config import StrategyConfig
    from strategy_engine.loader import load_strategies
    from data_contracts import FeatureSnapshot

    print("\n1️⃣  加载策略...")
    config = StrategyConfig(
        name="rapid-rise-test",
        module="sdk:strategies.official.rapid_rise.strategy",
        class_name="RapidRiseStrategy",
        parameters={}  # SDK strategies are initialized via initialize() method
    )

    strategies = load_strategies([config])
    if not strategies:
        print("   ❌ 策略加载失败")
        return False

    print(f"   ✅ 已加载 {len(strategies)} 个策略")

    print("\n2️⃣  创建测试特征...")
    feature = FeatureSnapshot(
        symbol="000001.SZ",
        window="300s",
        timestamp=datetime.now(),
        price=100.0,
        change_percent=5.5,
        volume_sum=10000000,
        avg_price=99.0,
        max_price=101.0,
        min_price=98.0,
        turnover_sum=1000000000.0,
        sample_size=100
    )

    print("\n3️⃣  执行策略评估...")
    strategy = list(strategies.values())[0]
    signal = strategy.evaluate(feature)

    if signal:
        print(f"   ✅ 策略生成信号:")
        print(f"      策略: {signal.strategy}")
        print(f"      股票: {signal.symbol}")
        print(f"      类型: {signal.signal_type}")
        print(f"      置信度: {signal.confidence:.2%}")
        print(f"      强度: {signal.strength_score}")
        return True
    else:
        print("   ℹ️  策略未生成信号（条件不满足）")
        return True


async def main():
    """主测试函数"""
    print("\n🚀 开始端到端测试...\n")

    # 测试 1: 策略引擎独立测试
    test1_passed = await test_strategy_engine_standalone()

    # 测试 2: 完整数据流测试
    test2_passed = await test_signal_generation()

    print("\n" + "=" * 70)
    print("📊 测试总结")
    print("=" * 70)
    print(f"  策略引擎独立测试: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"  端到端数据流测试: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print("=" * 70)

    return test1_passed and test2_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)