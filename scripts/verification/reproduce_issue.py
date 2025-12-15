import asyncio
import sys
import os
import json

# Add backend directory to sys.path
sys.path.append('/Users/wangfangchun/东风破/backend')

from core.data_sources import TencentDataSource, EastMoneyDataSource
from modules.options.service import OptionService

async def test_stock_data():
    print("Testing Stock Data Sources...")
    
    # Test Tencent Minute Data
    print("\n--- Testing Tencent Minute Data (sh600519) ---")
    async with TencentDataSource() as tencent:
        try:
            data = await tencent.get_minute_data('sh600519')
            if data:
                print(f"Success! Got {len(data['minute_data'])} points.")
                print("First point:", data['minute_data'][0])
                print("Last point:", data['minute_data'][-1])
            else:
                print("Failed to get minute data.")
        except Exception as e:
            print(f"Error: {e}")

    # Test Eastmoney K-line Data
    print("\n--- Testing Eastmoney K-line Data (sh600519) ---")
    async with EastMoneyDataSource() as eastmoney:
        try:
            data = await eastmoney.get_kline_data('sh600519', period='daily', count=5)
            if data and data['klines']:
                print(f"Success! Got {len(data['klines'])} klines.")
                print("First kline:", data['klines'][0])
                print("Last kline:", data['klines'][-1])
            else:
                print("Failed to get kline data.")
        except Exception as e:
            print(f"Error: {e}")

async def test_option_data():
    print("\nTesting Option Data Sources...")
    service = OptionService()
    await service.initialize()
    
    # Test Option Minute Data (using a known option code from the code)
    option_code = "10004603" # 50ETF购12月2800
    print(f"\n--- Testing Option Minute Data ({option_code}) ---")
    try:
        data = await service.get_minute_data(option_code)
        if data and data.get('minute_data'):
            print(f"Success! Got {len(data['minute_data'])} points.")
            print("Source:", data.get('source'))
            print("First point:", data['minute_data'][0])
        else:
            print("Failed to get option minute data:", data)
    except Exception as e:
        print(f"Error: {e}")

    # Test Option K-line Data
    print(f"\n--- Testing Option K-line Data ({option_code}) ---")
    try:
        data = await service.get_kline_data(option_code)
        if data and data.get('klines'):
            print(f"Success! Got {len(data['klines'])} klines.")
            print("Source:", data.get('source'))
            print("First kline:", data['klines'][0])
        else:
            print("Failed to get option kline data:", data)
    except Exception as e:
        print(f"Error: {e}")
        
    await service.cleanup()

async def main():
    await test_stock_data()
    await test_option_data()

if __name__ == "__main__":
    asyncio.run(main())
