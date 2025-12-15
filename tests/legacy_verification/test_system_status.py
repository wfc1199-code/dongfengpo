#!/usr/bin/env python3
"""
系统状态检查工具
检查各个服务的运行状态和连接性
"""

import asyncio
import aiohttp
import time
from datetime import datetime

async def check_backend_api():
    """检查后端API状态"""
    print("🔍 检查后端API状态...")

    base_url = "http://localhost:9000"
    endpoints = [
        "/api/options/MO2510-C-7400/minute",
        "/api/market-scanner/hot-sectors?limit=5",
        "/api/limit-up/predictions?limit=5"
    ]

    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            try:
                url = f"{base_url}{endpoint}"
                start_time = time.time()
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response_time = time.time() - start_time
                    if response.status == 200:
                        print(f"✅ {endpoint} - OK ({response.status}) - {response_time:.2f}s")
                    else:
                        print(f"❌ {endpoint} - ERROR ({response.status}) - {response_time:.2f}s")
            except Exception as e:
                print(f"❌ {endpoint} - FAILED: {str(e)}")

async def check_websocket():
    """检查WebSocket连接"""
    print("\n🔍 检查WebSocket连接...")

    try:
        import websockets
        uri = "ws://localhost:9000/ws"

        async with websockets.connect(uri, timeout=5) as websocket:
            print("✅ WebSocket连接成功")

            # 尝试接收一条消息
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=2)
                print(f"📨 收到消息: {message[:100]}...")
            except asyncio.TimeoutError:
                print("⏰ WebSocket连接正常，但暂无消息推送")

    except Exception as e:
        print(f"❌ WebSocket连接失败: {str(e)}")

async def check_external_connectivity():
    """检查外部网络连接"""
    print("\n🔍 检查外部网络连接...")

    urls = [
        "https://push2.eastmoney.com/api/qt/stock/get",
        "https://searchapi.eastmoney.com/search/pinyin/search"
    ]

    async with aiohttp.ClientSession() as session:
        for url in urls:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        print(f"✅ {url.split('//')[1].split('/')[0]} - 连接正常")
                    else:
                        print(f"⚠️ {url.split('//')[1].split('/')[0]} - 状态码: {response.status}")
            except Exception as e:
                print(f"❌ {url.split('//')[1].split('/')[0]} - 连接失败: {str(e)}")

async def main():
    print(f"🚀 东风破系统状态检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    await check_backend_api()
    await check_websocket()
    await check_external_connectivity()

    print("\n" + "=" * 60)
    print("📊 检查完成")

if __name__ == "__main__":
    asyncio.run(main())