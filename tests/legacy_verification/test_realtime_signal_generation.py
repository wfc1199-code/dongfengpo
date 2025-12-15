#!/usr/bin/env python3
"""
实时信号生成测试

向 Redis 特征频道发布模拟数据，验证 strategy-engine 能否生成信号
"""

import asyncio
import json
from datetime import datetime

import redis.asyncio as aioredis


async def publish_test_features():
    """发布测试特征数据到 Redis"""
    print("=" * 70)
    print("🧪 实时信号生成测试")
    print("=" * 70)

    # 连接 Redis
    print("\n1️⃣  连接 Redis...")
    redis_client = await aioredis.from_url(
        "redis://localhost:6379",
        encoding="utf-8",
        decode_responses=True
    )

    try:
        await redis_client.ping()
        print("   ✅ Redis 连接成功")
    except Exception as e:
        print(f"   ❌ Redis 连接失败: {e}")
        return

    # 准备多组测试数据
    test_cases = [
        {
            "name": "强势拉升股票",
            "feature": {
                "symbol": "000001.SZ",
                "window": "300s",
                "timestamp": datetime.now().isoformat(),
                "price": 15.50,
                "change_percent": 7.5,  # 涨幅7.5%
                "volume_sum": 50000000,
                "avg_price": 15.00,
                "max_price": 15.80,
                "min_price": 14.80,
                "turnover_sum": 750000000.0,
                "sample_size": 150
            }
        },
        {
            "name": "普通涨幅股票",
            "feature": {
                "symbol": "000002.SZ",
                "window": "300s",
                "timestamp": datetime.now().isoformat(),
                "price": 28.30,
                "change_percent": 2.1,  # 涨幅2.1%
                "volume_sum": 10000000,
                "avg_price": 28.00,
                "max_price": 28.50,
                "min_price": 27.80,
                "turnover_sum": 280000000.0,
                "sample_size": 100
            }
        },
        {
            "name": "下跌股票",
            "feature": {
                "symbol": "000003.SZ",
                "window": "300s",
                "timestamp": datetime.now().isoformat(),
                "price": 42.10,
                "change_percent": -1.5,  # 跌幅1.5%
                "volume_sum": 8000000,
                "avg_price": 42.50,
                "max_price": 43.00,
                "min_price": 42.00,
                "turnover_sum": 340000000.0,
                "sample_size": 80
            }
        }
    ]

    # 发布特征数据
    print("\n2️⃣  发布测试特征...")
    feature_channel = "dfp:features"

    for i, test_case in enumerate(test_cases, 1):
        feature = test_case["feature"]
        name = test_case["name"]

        print(f"\n   📊 测试用例 {i}: {name}")
        print(f"      股票: {feature['symbol']}")
        print(f"      价格: {feature['price']} ({feature['change_percent']:+.2f}%)")
        print(f"      成交量: {feature['volume_sum']:,}")

        # 发布到 Redis
        await redis_client.publish(feature_channel, json.dumps(feature))
        print(f"      ✅ 已发布到 {feature_channel}")

        # 等待一小段时间让策略引擎处理
        await asyncio.sleep(0.5)

    # 等待策略引擎处理
    print("\n3️⃣  等待策略引擎处理...")
    print("   ⏳ 等待 5 秒...")
    await asyncio.sleep(5)

    # 检查信号流
    print("\n4️⃣  检查生成的信号...")
    signal_stream = "dfp:signals"

    try:
        # 读取最新的信号
        messages = await redis_client.xrevrange(signal_stream, count=10)

        if messages:
            print(f"   ✅ 发现 {len(messages)} 个信号:\n")

            for msg_id, msg_data in messages:
                payload = json.loads(msg_data.get('payload', '{}'))

                print(f"   📈 信号 [{msg_id}]")
                print(f"      策略: {payload.get('strategy', 'N/A')}")
                print(f"      股票: {payload.get('symbol', 'N/A')}")
                print(f"      类型: {payload.get('signal_type', 'N/A')}")
                print(f"      置信度: {payload.get('confidence', 0):.2%}")
                print(f"      强度分: {payload.get('strength_score', 0):.2f}")

                reasons = payload.get('reasons', [])
                if reasons:
                    print(f"      原因: {', '.join(reasons)}")

                metadata = payload.get('metadata', {})
                if metadata:
                    print(f"      元数据: {json.dumps(metadata, indent=10, ensure_ascii=False)}")
                print()
        else:
            print("   ⚠️  未发现信号")
            print("   💡 可能原因:")
            print("      - 策略引擎未运行")
            print("      - 特征数据不满足策略条件")
            print("      - Redis 流配置不匹配")

    except Exception as e:
        print(f"   ❌ 读取信号失败: {e}")

    # 统计信息
    print("\n5️⃣  统计信息...")
    try:
        stream_info = await redis_client.xinfo_stream(signal_stream)
        print(f"   信号流长度: {stream_info.get('length', 0)}")
        print(f"   第一个信号ID: {stream_info.get('first-entry', ['N/A'])[0]}")
        print(f"   最后一个信号ID: {stream_info.get('last-entry', ['N/A'])[0]}")
    except Exception as e:
        print(f"   ℹ️  无法获取流统计: {e}")

    # 清理
    print("\n6️⃣  清理...")
    await redis_client.aclose()
    print("   ✅ 已关闭连接")

    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(publish_test_features())