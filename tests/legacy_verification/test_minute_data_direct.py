#!/usr/bin/env python3
"""
直接测试多源期权服务的分时数据获取
"""

import asyncio
import sys
import os

# 添加后端路径
sys.path.append('/Users/wangfangchun/东风破/backend')

from services.multi_source_option_service import MultiSourceOptionService

async def test_minute_data():
    """测试期权分时数据获取"""

    print("=== 测试多源期权服务 ===")

    service = MultiSourceOptionService()

    print("\n✅ 服务创建完成")

    # 测试多个期权代码
    test_codes = [
        "10002700",      # 原始代码
        "10004603.SH",   # 搜索到的代码
        "10005201.SH",   # 搜索到的代码
        "90005854",      # 另一个代码
        "MO2511-C-7400", # ETF期权格式
    ]

    for code in test_codes:
        print(f"\n📊 测试期权代码: {code}")

        try:
            # 先搜索期权信息
            print(f"  🔍 搜索期权信息...")
            search_results = await service.search_options(code, limit=1)
            print(f"  搜索结果: {len(search_results)} 个")

            if search_results:
                info = search_results[0]
                print(f"  找到期权: {info.get('name', 'N/A')}")
                print(f"  标的: {info.get('underlying', 'N/A')}")
                print(f"  行权价: {info.get('strike_price', 'N/A')}")
                print(f"  类型: {info.get('type', 'N/A')}")

            # 获取分时数据
            print(f"  📈 获取分时数据...")
            minute_data = await service.get_option_minute_data(code)
            print(f"  分时数据: {len(minute_data)} 条")

            if minute_data:
                print(f"  前3条数据:")
                for i, data in enumerate(minute_data[:3]):
                    print(f"    {i+1}: {data}")
            else:
                print(f"  ❌ 无分时数据")

        except Exception as e:
            print(f"  ❌ 错误: {e}")

    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    asyncio.run(test_minute_data())