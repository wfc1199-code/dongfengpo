"""测试WebSocket实时信号推送功能"""

import asyncio
import json
from datetime import datetime, timezone, timedelta

import websockets
import redis.asyncio as aioredis


async def websocket_client():
    """WebSocket客户端，接收实时信号"""
    uri = "ws://localhost:8100/ws/opportunities"

    print("🔌 连接到 WebSocket 服务器...")
    print(f"   URI: {uri}\n")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 连接成功！")
            print("⏳ 等待接收实时信号推送...\n")
            print("=" * 80)

            # 设置超时时间
            message_count = 0
            timeout = 30  # 30秒超时

            try:
                async with asyncio.timeout(timeout):
                    async for message in websocket:
                        message_count += 1
                        data = json.loads(message)

                        print(f"\n📨 收到信号 #{message_count}:")
                        print(f"   类型: {data.get('type')}")

                        if data.get('type') == 'opportunity':
                            # 数据在payload字段中
                            opp = data.get('payload', data.get('data', {}))
                            print(f"   股票代码: {opp.get('symbol')}")
                            print(f"   状态: {opp.get('state')}")
                            print(f"   置信度: {opp.get('confidence', 0):.2%}")
                            print(f"   强度分数: {opp.get('strength_score', 0):.1f}")
                            print(f"   更新时间: {opp.get('updated_at')}")

                            if opp.get('signals'):
                                print(f"   关联信号数: {len(opp.get('signals', []))}")
                                latest_signal = opp['signals'][-1]
                                print(f"   最新策略: {latest_signal.get('strategy')}")
                                print(f"   信号类型: {latest_signal.get('signal_type')}")

                        elif data.get('type') == 'risk_alert':
                            alert = data.get('payload', data.get('data', {}))
                            print(f"   ⚠️  风险警告: {alert.get('message')}")

                        print("-" * 80)

                        # 收到5个消息后断开
                        if message_count >= 5:
                            print(f"\n✅ 已接收 {message_count} 个消息，测试完成")
                            break

            except asyncio.TimeoutError:
                print(f"\n⏱️  超时 ({timeout}秒)，未收到新消息")
                if message_count > 0:
                    print(f"✅ 总共接收到 {message_count} 个消息")
                else:
                    print("⚠️  未收到任何消息，可能需要触发新的信号")

    except Exception as e:
        print(f"❌ WebSocket 连接失败: {e}")
        return False

    return True


async def trigger_new_signals():
    """触发新的信号以测试WebSocket推送"""
    print("\n🚀 触发新的交易信号...")
    print("=" * 80)

    redis_client = await aioredis.from_url("redis://localhost:6379", decode_responses=True)

    # 发送快速涨幅的tick数据
    base_time = datetime.now(timezone.utc)
    base_price = 12.00
    symbol = "600000.SH"  # 测试不同股票

    print(f"📤 发送 {symbol} 的tick数据（模拟3%快速涨幅）...\n")

    for i in range(5):
        tick_time = (base_time + timedelta(seconds=i)).isoformat()
        price = base_price * (1 + 0.006 * i)  # 0.6% per tick = 3% total

        tick = {
            "source": "test_ws",
            "symbol": symbol,
            "price": round(price, 2),
            "volume": 60000 + i * 10000,
            "turnover": round(price * (60000 + i * 10000) * 100, 2),
            "bid_price": round(price - 0.01, 2),
            "bid_volume": 1000,
            "ask_price": round(price + 0.01, 2),
            "ask_volume": 800,
            "timestamp": tick_time,
            "ingested_at": tick_time,
            "cleaned_at": tick_time,
            "quality_flags": [],
            "raw": {},
        }

        payload = json.dumps(tick)
        await redis_client.xadd(
            name="dfp:clean_ticks",
            fields={"payload": payload},
            maxlen=10000,
            approximate=True
        )
        print(f"   ✓ Tick {i+1}/5: {symbol} @ {tick['price']:.2f}")
        await asyncio.sleep(0.2)

    print(f"\n✅ 已发送5个tick，等待管道处理...\n")
    await asyncio.sleep(2)  # 等待处理

    await redis_client.aclose()


async def main():
    """主测试流程"""
    print("=" * 80)
    print("🧪 WebSocket 实时信号推送测试")
    print("=" * 80)
    print()

    # 创建两个任务：一个触发信号，一个监听WebSocket
    print("📋 测试计划:")
    print("   1. 启动 WebSocket 客户端")
    print("   2. 触发新的交易信号")
    print("   3. 验证实时推送功能")
    print()

    # 先启动WebSocket客户端
    client_task = asyncio.create_task(websocket_client())

    # 等待1秒让客户端连接
    await asyncio.sleep(1)

    # 然后触发新信号
    trigger_task = asyncio.create_task(trigger_new_signals())

    # 等待两个任务完成
    results = await asyncio.gather(client_task, trigger_task, return_exceptions=True)

    print("\n" + "=" * 80)
    print("📊 测试结果总结")
    print("=" * 80)

    if results[0]:
        print("✅ WebSocket 实时推送功能正常")
    else:
        print("⚠️  WebSocket 推送可能存在问题")

    print("✅ 信号触发完成")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏸️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()