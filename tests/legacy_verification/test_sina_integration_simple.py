#!/usr/bin/env python3
"""
测试新浪财经中证1000期权分时图数据源集成（简化版）
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_sina_fetcher_direct():
    """直接测试新浪财经数据获取器"""
    print("=" * 60)
    print("测试新浪财经中证1000期权数据获取器")
    print("=" * 60)
    
    try:
        # 直接导入和测试
        from backend.services.sina_mo1000_fetcher import SinaMO1000Fetcher
        
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
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_api_call():
    """测试API调用"""
    print("\n" + "=" * 60)
    print("测试API调用")
    print("=" * 60)
    
    import aiohttp
    
    base_url = "http://localhost:9000"
    test_code = "MO2510-C-7400"
    
    print(f"测试期权: {test_code}")
    print("注意: 需要后端服务运行在 localhost:9000")
    
    try:
        async with aiohttp.ClientSession() as session:
            # 测试分时数据API
            url = f"{base_url}/api/options/{test_code}/minute"
            print(f"请求URL: {url}")
            
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                print(f"响应状态: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"响应数据: {data}")
                    
                    if data.get('status') == 'success':
                        minute_count = len(data.get('data', []))
                        print(f"✅ 分时数据API: {minute_count}个数据点")
                    else:
                        print(f"❌ 分时数据API: {data.get('error', '未知错误')}")
                else:
                    text = await response.text()
                    print(f"❌ HTTP错误: {text}")
                    
    except aiohttp.ClientConnectorError:
        print("❌ 无法连接到后端服务，请确保服务运行在 localhost:9000")
    except Exception as e:
        print(f"❌ API调用异常: {e}")


async def main():
    """主测试函数"""
    print("新浪财经中证1000期权分时图数据源集成测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试新浪财经数据获取器
    await test_sina_fetcher_direct()
    
    # 测试API调用
    await test_api_call()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
