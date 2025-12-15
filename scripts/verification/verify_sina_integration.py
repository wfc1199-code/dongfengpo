#!/usr/bin/env python3
"""
验证新浪财经中证1000期权分时图数据源集成
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_integration():
    """测试集成"""
    print("=" * 60)
    print("验证新浪财经中证1000期权分时图数据源集成")
    print("=" * 60)
    
    try:
        # 测试新浪财经数据获取器
        from backend.services.sina_mo1000_fetcher import SinaMO1000Fetcher
        
        async with SinaMO1000Fetcher() as fetcher:
            print("\n1. 测试新浪财经数据获取器")
            minute_data = await fetcher.get_option_minute_data("MO2510-C-7400")
            
            if minute_data and minute_data.get('status') == 'success':
                data_points = len(minute_data.get('minute_data', []))
                print(f"   ✅ 新浪财经数据获取器: {data_points}个数据点")
                print(f"   ✅ 数据源: {minute_data.get('source', '未知')}")
            else:
                print(f"   ❌ 新浪财经数据获取器失败")
        
        # 测试RealTimeOptionFetcher
        print("\n2. 测试RealTimeOptionFetcher")
        from backend.real_option_data_fetcher import RealTimeOptionFetcher
        
        async with RealTimeOptionFetcher() as fetcher:
            data = await fetcher.get_option_minute_data("MO2510-C-7400")
            
            if data and data.get('status') == 'success':
                data_points = len(data.get('minute_data', []))
                print(f"   ✅ RealTimeOptionFetcher: {data_points}个数据点")
                print(f"   ✅ 数据源: {data.get('source', '未知')}")
            else:
                print(f"   ❌ RealTimeOptionFetcher失败: {data.get('message', '未知错误')}")
        
        # 测试API端点
        print("\n3. 测试API端点")
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            url = "http://localhost:9000/api/options/MO2510-C-7400/minute"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    data_points = len(data.get('data', []))
                    print(f"   ✅ API端点: {data_points}个数据点")
                    print(f"   ✅ 状态: {data.get('status')}")
                else:
                    print(f"   ❌ API端点失败: HTTP {response.status}")
        
        print("\n" + "=" * 60)
        print("✅ 集成验证完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_integration())
