#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试期权分时数据格式
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.akshare_mo1000_fetcher import MO1000OptionDataFetcher
import json

def debug_minute_data():
    """调试分时数据格式"""
    print("🔍 调试期权分时数据格式")
    print("=" * 80)

    fetcher = MO1000OptionDataFetcher()

    # 测试期权代码
    option_code = "MO1000-C-7500"

    print(f"📊 获取期权分时数据: {option_code}")
    result = fetcher.get_option_minute_data(option_code)

    if result and result.get("status") == "success":
        print("✅ API调用成功")

        # 检查数据结构
        minute_data = result.get("minute_data", [])

        print(f"\n📋 数据结构分析:")
        print(f"   顶级键: {list(result.keys())}")
        print(f"   minute_data长度: {len(minute_data)}")

        if minute_data:
            print(f"   minute_data[0]键: {list(minute_data[0].keys())}")
            print(f"   第一个数据点: {minute_data[0]}")

            print(f"\n⏰ 时间序列检查:")
            print(f"   前5个时间: {[item['time'] for item in minute_data[:5]]}")
            print(f"   后5个时间: {[item['time'] for item in minute_data[-5:]]}")

            print(f"\n💰 价格序列检查:")
            prices = [item['price'] for item in minute_data[:10]]
            print(f"   前10个价格: {prices}")

            # 检查是否有异常值
            price_stats = {
                'min': min(item['price'] for item in minute_data),
                'max': max(item['price'] for item in minute_data),
                'avg': sum(item['price'] for item in minute_data) / len(minute_data)
            }
            print(f"   价格统计: {price_stats}")

            # 检查分时图问题
            print(f"\n🔍 分时图问题分析:")

            # 1. 检查时间是否连续
            times = [item['time'] for item in minute_data]
            expected_start = "09:30"
            expected_end = "15:00"
            actual_start = times[0]
            actual_end = times[-1]

            print(f"   时间范围: {actual_start} - {actual_end}")
            print(f"   预期范围: {expected_start} - {expected_end}")

            if actual_start != expected_start:
                print(f"   ❌ 开盘时间错误，应为{expected_start}，实际为{actual_start}")
            else:
                print(f"   ✅ 开盘时间正确")

            if actual_end != expected_end:
                print(f"   ❌ 收盘时间错误，应为{expected_end}，实际为{actual_end}")
            else:
                print(f"   ✅ 收盘时间正确")

            # 2. 检查价格变化是否合理
            first_price = minute_data[0]['price']
            last_price = minute_data[-1]['price']
            price_change = (last_price - first_price) / first_price * 100

            print(f"   价格变化: {price_change:.2f}%")
            if abs(price_change) > 20:
                print(f"   ❌ 价格变化过大，可能存在数据异常")
            else:
                print(f"   ✅ 价格变化合理")

            # 3. 检查成交量
            volumes = [item['volume'] for item in minute_data[:10]]
            avg_volume = sum(volumes) / len(volumes)
            print(f"   平均成交量: {avg_volume:.0f}")

            # 4. 检查数据格式是否符合前端预期
            print(f"\n📡 前端API格式检查:")

            # 前端期望格式
            expected_keys = {'time', 'price', 'volume', 'amount', 'avg_price', 'change_percent'}
            actual_keys = set(minute_data[0].keys())

            if expected_keys.issubset(actual_keys):
                print(f"   ✅ 前端期望的键都存在")
            else:
                missing = expected_keys - actual_keys
                print(f"   ❌ 缺少前端期望的键: {missing}")

            # 前端API路径应该是 /api/options/{option_code}/minute
            # 但MO1000的API可能不同
            print(f"\n🌐 API端点信息:")
            print(f"   后端类: MO1000OptionDataFetcher")
            print(f"   方法: get_option_minute_data('{option_code}')")
            print(f"   前端期望: GET /api/options/{option_code}/minute")

    else:
        print("❌ API调用失败")
        if result:
            print(f"   错误信息: {result.get('error', '未知错误')}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    debug_minute_data()