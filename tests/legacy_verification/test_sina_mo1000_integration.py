#!/usr/bin/env python3
"""
测试新浪财经中证1000期权分时图数据源集成
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.sina_mo1000_fetcher import SinaMO1000Fetcher
from backend.services.real_option_data_service import RealOptionDataService
from backend.services.real_option_data_fetcher import RealOptionDataFetcher
from backend.modules.options.low_latency_service import LowLatencyOptionDataService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_sina_fetcher():
    """测试新浪财经数据获取器"""
    print("=" * 60)
    print("测试新浪财经中证1000期权数据获取器")
    print("=" * 60)
    
    async with SinaMO1000Fetcher() as fetcher:
        # 测试期权代码格式化
        test_codes = ["MO2510-C-7400", "MO2511-P-7400", "MO2512-C-7500"]
        
        for code in test_codes:
            print(f"\n测试期权代码: {code}")
            
            # 测试代码格式化
            sina_code = fetcher._format_option_code_for_sina(code)
            print(f"  格式化后: {sina_code}")
            
            # 测试实时数据
            print(f"  获取实时数据...")
            realtime = await fetcher.get_option_realtime(code)
            if realtime:
                print(f"  ✅ 实时数据: 价格={realtime.get('current_price')}, 涨跌幅={realtime.get('change_percent')}%")
            else:
                print(f"  ❌ 实时数据获取失败")
            
            # 测试分时数据
            print(f"  获取分时数据...")
            minute_data = await fetcher.get_option_minute_data(code)
            if minute_data and minute_data.get('status') == 'success':
                data_points = len(minute_data.get('minute_data', []))
                print(f"  ✅ 分时数据: {data_points}个数据点")
            else:
                print(f"  ❌ 分时数据获取失败")
        
        # 测试搜索功能
        print(f"\n测试期权搜索...")
        options = await fetcher.search_mo1000_options("中证1000", 5)
        print(f"✅ 搜索到 {len(options)} 个期权:")
        for option in options:
            print(f"  - {option['code']}: {option['name']} (价格: {option['current_price']})")


async def test_integrated_services():
    """测试集成的期权服务"""
    print("\n" + "=" * 60)
    print("测试集成的期权服务")
    print("=" * 60)
    
    # 测试真实期权数据服务
    print("\n1. 测试真实期权数据服务")
    option_service = RealOptionDataService()
    await option_service.__aenter__()
    
    try:
        mo1000_options = await option_service._get_1000_options(5)
        print(f"✅ 获取到 {len(mo1000_options)} 个中证1000期权")
        for option in mo1000_options:
            print(f"  - {option['code']}: {option['name']}")
    except Exception as e:
        print(f"❌ 获取中证1000期权失败: {e}")
    
    await option_service.__aexit__(None, None, None)
    
    # 测试期权数据获取器
    print("\n2. 测试期权数据获取器")
    fetcher = RealOptionDataFetcher()
    
    test_code = "MO2510-C-7400"
    print(f"测试期权: {test_code}")
    
    try:
        minute_data = await fetcher.get_option_minute_data(test_code)
        if minute_data:
            print(f"✅ 获取到 {len(minute_data)} 条分时数据")
        else:
            print(f"❌ 分时数据获取失败")
    except Exception as e:
        print(f"❌ 分时数据获取异常: {e}")


async def test_api_endpoints():
    """测试API端点"""
    print("\n" + "=" * 60)
    print("测试API端点")
    print("=" * 60)
    
    import aiohttp
    
    base_url = "http://localhost:9000"
    test_codes = ["MO2510-C-7400", "MO2511-P-7400"]
    
    async with aiohttp.ClientSession() as session:
        for code in test_codes:
            print(f"\n测试期权: {code}")
            
            # 测试分时数据API
            try:
                url = f"{base_url}/api/options/{code}/minute"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 'success':
                            minute_count = len(data.get('data', []))
                            print(f"  ✅ 分时数据API: {minute_count}个数据点")
                        else:
                            print(f"  ❌ 分时数据API: {data.get('error', '未知错误')}")
                    else:
                        print(f"  ❌ 分时数据API: HTTP {response.status}")
            except Exception as e:
                print(f"  ❌ 分时数据API异常: {e}")
            
            # 测试实时数据API
            try:
                url = f"{base_url}/api/options/{code}/realtime"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 'success':
                            price = data.get('current_price', 0)
                            print(f"  ✅ 实时数据API: 价格={price}")
                        else:
                            print(f"  ❌ 实时数据API: {data.get('error', '未知错误')}")
                    else:
                        print(f"  ❌ 实时数据API: HTTP {response.status}")
            except Exception as e:
                print(f"  ❌ 实时数据API异常: {e}")


async def main():
    """主测试函数"""
    print("新浪财经中证1000期权分时图数据源集成测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 测试新浪财经数据获取器
        await test_sina_fetcher()
        
        # 测试集成的服务
        await test_integrated_services()
        
        # 测试API端点（需要后端服务运行）
        print("\n注意: API端点测试需要后端服务运行在 localhost:9000")
        # await test_api_endpoints()
        
        print("\n" + "=" * 60)
        print("✅ 测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
