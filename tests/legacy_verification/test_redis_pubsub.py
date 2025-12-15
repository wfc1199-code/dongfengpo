#!/usr/bin/env python3
"""测试 Redis Pubsub 是否正常工作"""

import asyncio
import json
from datetime import datetime

import redis.asyncio as aioredis


async def test_pubsub():
    """测试发布订阅"""
    print("=" * 70)
    print("🧪 Redis Pubsub 测试")
    print("=" * 70)

    # 创建两个客户端：一个订阅，一个发布
    print("\n1️⃣  创建 Redis 客户端...")
    pub_client = await aioredis.from_url("redis://localhost:6379", decode_responses=True)
    sub_client = await aioredis.from_url("redis://localhost:6379", decode_responses=True)

    print("   ✅ 客户端创建成功")

    # 订阅频道
    print("\n2️⃣  订阅 dfp:features 频道...")
    pubsub = sub_client.pubsub()
    await pubsub.subscribe("dfp:features")
    print("   ✅ 订阅成功")

    # 等待订阅确认
    print("\n3️⃣  等待订阅确认...")
    while True:
        message = await pubsub.get_message(timeout=2.0)
        if message and message['type'] == 'subscribe':
            print(f"   ✅ 订阅确认: {message}")
            break

    # 发布测试消息
    print("\n4️⃣  发布测试消息...")
    test_data = {
        "symbol": "TEST.001",
        "window": "300s",
        "timestamp": datetime.now().isoformat(),
        "price": 100.0,
        "change_percent": 5.0,
        "volume_sum": 1000000,
        "avg_price": 99.0,
        "max_price": 101.0,
        "min_price": 98.0,
        "turnover_sum": 100000000.0,
        "sample_size": 100
    }

    num_receivers = await pub_client.publish("dfp:features", json.dumps(test_data))
    print(f"   ✅ 消息已发布，接收者数量: {num_receivers}")

    # 接收消息
    print("\n5️⃣  接收消息...")
    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)

    if message:
        print(f"   ✅ 接收到消息:")
        print(f"      类型: {message['type']}")
        print(f"      频道: {message['channel']}")
        print(f"      数据: {message['data'][:100]}..." if len(str(message['data'])) > 100 else f"      数据: {message['data']}")
    else:
        print("   ❌ 未接收到消息")

    # 清理
    print("\n6️⃣  清理...")
    await pubsub.unsubscribe("dfp:features")
    await pubsub.close()
    await pub_client.aclose()
    await sub_client.aclose()
    print("   ✅ 清理完成")

    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_pubsub())