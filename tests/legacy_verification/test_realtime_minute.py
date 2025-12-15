#!/usr/bin/env python3
"""
测试实时期权数据获取器的分时数据
"""

import asyncio
import sys
import os

# 添加后端路径
sys.path.append('/Users/wangfangchun/东风破/backend')

from real_option_data_fetcher import RealTimeOptionFetcher

async def test_realtime_minute_data():
    """测试实时期权分时数据"""

    print("=== 测试实时期权数据获取器 ===")

    fetcher = RealTimeOptionFetcher()

    async with fetcher:
        print("\n✅ 实时期权获取器初始化完成")

        # 测试多个期权代码
        test_codes = [
            "10004603",   # 50ETF购12月2800
            "90005854",   # 50ETF沽12月2800
            "10005201",   # 300ETF购12月4800
        ]

        for code in test_codes:
            print(f"\n📊 测试期权代码: {code}")

            try:
                # 获取分时数据
                print(f"  📈 获取实时期权分时数据...")
                minute_data = await fetcher.get_option_minute_data(code)

                print(f"  响应结构: {list(minute_data.keys())}")

                if 'minute_data' in minute_data:
                    data_points = minute_data['minute_data']
                    print(f"  分时数据: {len(data_points)} 条")

                    if data_points:
                        print(f"  最新价格: ¥{minute_data.get('current_price', 0)}")
                        print(f"  数据时间: {minute_data.get('data_time', 'N/A')}")
                        print(f"  涨跌幅: {minute_data.get('change_percent', 0)}%")

                        # 显示前3条数据
                        print(f"  前3条数据:")
                        for i, data in enumerate(data_points[:3]):
                            print(f"    {i+1}: {data['time']} - ¥{data['price']} - 成交量:{data['volume']}")

                        # 检查是否是模拟数据
                        if data_points and len(data_points) > 200:  # 通常模拟数据会有很多点
                            print(f"  ⚠️  可能是模拟数据（数据点过多）")
                        else:
                            print(f"  ✅ 可能是真实数据")
                    else:
                        print(f"  ❌ 无分时数据")
                else:
                    print(f"  ❌ 响应格式异常: 无 minute_data 字段")

            except Exception as e:
                print(f"  ❌ 错误: {e}")

    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    asyncio.run(test_realtime_minute_data())