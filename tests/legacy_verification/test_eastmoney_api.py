#!/usr/bin/env python3
"""
测试东方财富期权API
"""

import asyncio
import aiohttp
import json
import ssl
from datetime import datetime

async def test_eastmoney_suggest_api():
    """测试东方财富建议API"""
    print("🔍 测试东方财富建议API...")

    # 创建SSL上下文，忽略证书验证
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    connector = aiohttp.TCPConnector(ssl=ssl_context)

    # 东方财富建议API
    search_url = "https://searchapi.eastmoney.com/api/suggest/get"
    params = {
        'input': 'MO2510-C-7400',
        'type': '14',  # 期权类型
        'token': 'D43BF722C8E33BDC906FB84D85E326E8',
        'markettype': '',
        'mktnum': '',
        'jys': '',
        'classify': '',
        'securitytype': '',
        'status': '',
        'letter': ''
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://quote.eastmoney.com/',
        'Accept': 'application/json, text/plain, */*'
    }

    try:
        async with aiohttp.ClientSession(
            connector=connector,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=15)
        ) as session:

            print(f"📡 请求URL: {search_url}")
            print(f"📡 请求参数: {params}")

            async with session.get(search_url, params=params) as response:
                print(f"📊 响应状态: {response.status}")
                print(f"📊 响应头: {dict(response.headers)}")

                if response.status == 200:
                    data = await response.json()
                    print(f"✅ API调用成功")
                    print(f"📊 响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
                else:
                    text = await response.text()
                    print(f"❌ API调用失败: {response.status}")
                    print(f"📊 响应内容: {text[:500]}")

    except Exception as e:
        print(f"❌ 请求异常: {type(e).__name__}: {str(e)}")

async def test_alternative_search():
    """测试备用搜索API"""
    print("\n🔍 测试备用搜索API...")

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    connector = aiohttp.TCPConnector(ssl=ssl_context)

    # 尝试不同的搜索API
    urls = [
        "https://searchapi.eastmoney.com/search/pinyin/search",
        "https://search.eastmoney.com/suggest/get"
    ]

    for search_url in urls:
        print(f"\n📡 测试URL: {search_url}")

        try:
            async with aiohttp.ClientSession(
                connector=connector,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:

                params = {
                    'keyword': 'MO2510-C-7400',
                    'type': '30'
                }

                async with session.get(search_url, params=params) as response:
                    print(f"📊 状态码: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ 成功: {str(data)[:200]}...")
                    else:
                        print(f"❌ 失败: {await response.text()[:100]}")

        except Exception as e:
            print(f"❌ 异常: {str(e)}")

async def main():
    print(f"🚀 东方财富API测试 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    await test_eastmoney_suggest_api()
    await test_alternative_search()

    print("\n" + "=" * 60)
    print("📊 测试完成")

if __name__ == "__main__":
    asyncio.run(main())