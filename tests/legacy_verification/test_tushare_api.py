#!/usr/bin/env python3
"""
测试Tushare Pro API的正确接口
"""

import tushare as ts
import os
from datetime import datetime, timedelta

# 设置token
os.environ['TUSHARE_TOKEN'] = 'cadca97e190afb9d92d6df92985d40affdfe34f9a6fcbde1e4abda30'

# 初始化
pro = ts.pro_api()

def test_tushare_api():
    """测试Tushare API"""
    print("=" * 60)
    print("测试Tushare Pro API")
    print("=" * 60)

    try:
        # 1. 测试基础连接
        print("\n1. 测试基础连接...")
        # 获取交易日历
        cal = pro.trade_cal(exchange='SSE', start_date='20250120', end_date='20250123')
        print(f"获取交易日历成功: {len(cal)} 条记录")

        # 2. 检查期权相关接口
        print("\n2. 检查期权相关接口...")

        # 查看所有接口
        print("\n可用的期权相关接口:")
        all_methods = [method for method in dir(pro) if 'option' in method.lower()]
        for method in all_methods:
            print(f"  - {method}")

        # 3. 尝试获取期权基础信息
        print("\n3. 尝试获取期权基础信息...")
        try:
            # 尝试获取ETF期权基础信息
            # Tushare的期权接口可能需要特定参数
            df = pro.opt_basic(exchange='SSE')
            print(f"获取期权基础信息成功: {len(df)} 条记录")
            if not df.empty:
                print(df.head())
        except Exception as e:
            print(f"获取期权基础信息失败: {e}")

        # 4. 获取股票信息（测试基础功能）
        print("\n4. 测试获取股票信息...")
        try:
            # 获取50ETF信息
            df = pro.daily(ts_code='510050.SH', start_date='20250122', end_date='20250123')
            if not df.empty:
                print(f"获取50ETF数据成功:")
                print(df[['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol']].head())
        except Exception as e:
            print(f"获取50ETF数据失败: {e}")

        # 5. 获取期权日线数据
        print("\n5. 尝试获取期权日线数据...")
        try:
            # 尝试一个期权代码
            df = pro.opt_daily(ts_code='10004603.SH', trade_date='20250122')
            if not df.empty:
                print(f"获取期权日线数据成功:")
                print(df.head())
            else:
                print("期权日线数据为空")
        except Exception as e:
            print(f"获取期权日线数据失败: {e}")

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tushare_api()