#!/usr/bin/env python3
"""
测试Tushare返回的字段
"""

import os
import pandas as pd

# 设置token
os.environ['TUSHARE_TOKEN'] = 'cadca97e190afb9d92d6df92985d40affdfe34f9a6fcbde1e4abda30'

import tushare as ts

# 初始化
ts.set_token(os.environ['TUSHARE_TOKEN'])
pro = ts.pro_api()

print("测试Tushare期权基础信息接口...")
print("=" * 60)

try:
    # 获取上交所期权基础信息
    df = pro.opt_basic(exchange='SSE', limit=5)

    if df is not None and not df.empty:
        print("成功获取数据！")
        print("\n字段列表:")
        print(df.columns.tolist())
        print("\n前5条记录:")
        print(df.to_string())

        # 查看数据类型
        print("\n字段类型:")
        print(df.dtypes)

    else:
        print("未获取到数据")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试期权日线数据接口...")

try:
    # 获取期权日线数据
    df2 = pro.opt_daily(
        ts_code='10004603.SH',
        trade_date='20250122'
    )

    if df2 is not None and not df2.empty:
        print("成功获取日线数据！")
        print("\n字段列表:")
        print(df2.columns.tolist())
        print("\n数据:")
        print(df2.to_string())

    else:
        print("未获取到日线数据")

except Exception as e:
    print(f"错误: {e}")