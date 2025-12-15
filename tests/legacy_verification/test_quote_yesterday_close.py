#!/usr/bin/env python3
"""
测试行情API返回的昨收价格原始值
"""

import asyncio
import sys
sys.path.insert(0, 'backend')

from modules.options.data_layer.real_data_provider import real_data_provider

async def test_quote_yesterday_close():
    """测试行情API昨收价格"""
    
    option_code = 'MO2511-P-7400'
    
    print("=" * 60)
    print("测试行情API昨收价格")
    print("=" * 60)
    
    # 获取行情
    quote = await real_data_provider.get_option_quote(option_code)
    
    if quote:
        print(f"\n【行情数据】")
        print(f"  当前价: {quote['current_price']}")
        print(f"  开盘价: {quote['open_price']}")
        print(f"  昨收价: {quote['yesterday_close']}")
    
    # 获取日K线
    klines = await real_data_provider.get_kline_data(option_code, 'daily', 1)
    
    if klines:
        kline = klines[0]
        print(f"\n【日K线数据】")
        print(f"  日期: {kline['date']}")
        print(f"  收盘: {kline['close']}")
        print(f"  昨收: {kline['yesterday_close']}")
    
    print(f"\n【对比】")
    if quote and klines:
        print(f"  行情昨收: {quote['yesterday_close']}")
        print(f"  K线昨收: {kline['yesterday_close']}")
        
        if abs(quote['yesterday_close'] - kline['yesterday_close']) < 1.0:
            print("  ✅ 一致")
        else:
            ratio = kline['yesterday_close'] / quote['yesterday_close']
            print(f"  ❌ 不一致，K线是行情的{ratio:.0f}倍")
    
    print("\n" + "=" * 60)
    await real_data_provider.close()

if __name__ == "__main__":
    asyncio.run(test_quote_yesterday_close())
