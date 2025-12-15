#!/usr/bin/env python3
"""
直接测试东方财富API原始数据
查看分钟K线的涨跌额是相对什么计算的
"""

import asyncio
import aiohttp

async def test_raw_api():
    """测试原始API"""
    
    # 期权代码
    option_code = 'MO2511-P-7400'
    secid = '116.90005854'  # MO2511-P-7400的secid
    
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    
    # 测试5分钟K线
    params = {
        'secid': secid,
        'klt': '5',  # 5分钟
        'fqt': '0',
        'lmt': 10,
        'end': '20500101',
        'iscca': '1',
        'fields1': 'f1,f2,f3,f4,f5,f6,f7,f8',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            data = await response.json()
            
            print("=" * 80)
            print("5分钟K线原始数据（最后10根）")
            print("=" * 80)
            print("\n格式: 日期,开,收,高,低,量,额,振幅%,涨跌幅%,涨跌额,换手率\n")
            
            klines = data.get('data', {}).get('klines', [])
            for kline_str in klines[-10:]:
                print(kline_str)
            
            print("\n" + "=" * 80)
            print("解析数据：")
            print("=" * 80)
            
            for kline_str in klines[-5:]:
                parts = kline_str.split(',')
                date = parts[0]
                open_price = float(parts[1])
                close_price = float(parts[2])
                change = float(parts[9]) if parts[9] else 0
                
                # 从涨跌额反推昨收
                yesterday_close = close_price - change
                
                print(f"\n{date}:")
                print(f"  开盘: {open_price}")
                print(f"  收盘: {close_price}")
                print(f"  涨跌额: {change}")
                print(f"  反推昨收: {yesterday_close}")

if __name__ == "__main__":
    asyncio.run(test_raw_api())
