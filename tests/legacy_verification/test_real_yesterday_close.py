#!/usr/bin/env python3
"""
直接测试东方财富API获取真实的昨收价格
"""

import asyncio
import aiohttp

async def test_real_yesterday_close():
    """测试真实的昨收价格"""
    
    option_code = 'MO2511-P-7400'
    secid = '116.90005854'
    
    print("=" * 60)
    print("测试真实的昨收价格")
    print("=" * 60)
    
    # 测试日K线API
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        'secid': secid,
        'klt': '101',  # 日K
        'fqt': '0',
        'lmt': 3,
        'end': '20500101',
        'iscca': '1',
        'fields1': 'f1,f2,f3,f4,f5,f6,f7,f8',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            data = await response.json()
            
            print("\n【最近3个交易日K线原始数据】")
            klines = data.get('data', {}).get('klines', [])
            for kline_str in klines:
                print(kline_str)
            
            print("\n【解析后的数据】")
            for kline_str in klines:
                parts = kline_str.split(',')
                date = parts[0]
                close = float(parts[2])
                change = float(parts[9]) if parts[9] else 0
                
                # 从涨跌额反推昨收
                yesterday_close = close - change
                
                print(f"\n{date}:")
                print(f"  收盘: {close}")
                print(f"  涨跌额: {change}")
                print(f"  反推昨收: {yesterday_close}")
            
            # 验证：今天的昨收应该等于昨天的收盘
            if len(klines) >= 2:
                today_kline = klines[-1].split(',')
                yesterday_kline = klines[-2].split(',')
                
                today_close = float(today_kline[2])
                today_change = float(today_kline[9]) if today_kline[9] else 0
                today_yesterday_close = today_close - today_change
                
                yesterday_close_price = float(yesterday_kline[2])
                
                print(f"\n【验证】")
                print(f"  今天反推的昨收: {today_yesterday_close}")
                print(f"  昨天实际收盘: {yesterday_close_price}")
                
                if abs(today_yesterday_close - yesterday_close_price) < 1.0:
                    print(f"  ✅ 一致！")
                else:
                    print(f"  ❌ 不一致！")

if __name__ == "__main__":
    asyncio.run(test_real_yesterday_close())
