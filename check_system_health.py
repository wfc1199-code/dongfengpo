#!/usr/bin/env python3
"""快速系统健康检查"""

import asyncio
import aiohttp
import redis.asyncio as aioredis


async def main():
    print("\n" + "=" * 80)
    print("🏥 东风破系统健康检查")
    print("=" * 80 + "\n")

    # 检查HTTP服务
    services = {
        "Signal-API (8000)": "http://localhost:8000/health",
        "Backtest-Service (8200)": "http://localhost:8200/health",
        "API Gateway (8888)": "http://localhost:8888/gateway/health",
        "Signal-Streamer (8100)": "http://localhost:8100/health",
    }

    print("📊 HTTP服务检查:")
    async with aiohttp.ClientSession() as session:
        for name, url in services.items():
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=2)) as response:
                    if response.status == 200:
                        print(f"   ✅ {name}")
                    else:
                        print(f"   ⚠️  {name} (状态码: {response.status})")
            except Exception as e:
                print(f"   ❌ {name} (错误: {e})")

    # 检查Redis
    print("\n📦 Redis检查:")
    try:
        redis_client = await aioredis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_client.ping()
        print("   ✅ Redis运行正常")

        # 检查数据流
        print("\n📈 数据流检查:")
        streams = {
            "dfp:clean_ticks": "清洗后的Tick数据",
            "dfp:strategy_signals": "策略信号",
            "dfp:opportunities": "交易机会"
        }

        for stream, desc in streams.items():
            try:
                length = await redis_client.xlen(stream)
                print(f"   - {desc.ljust(20)}: {length:,} 条")
            except:
                print(f"   - {desc.ljust(20)}: 0 条")

        await redis_client.aclose()

    except Exception as e:
        print(f"   ❌ Redis连接失败: {e}")

    print("\n" + "=" * 80)
    print("✅ 健康检查完成")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())