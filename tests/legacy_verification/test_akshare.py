#!/usr/bin/env python3
import time
import akshare as ak

print("测试akshare数据获取速度...")

# 测试1: 获取个股信息
start = time.time()
try:
    info = ak.stock_individual_info_em(symbol='000001')
    print(f"✅ 获取个股信息成功，耗时: {time.time() - start:.2f}秒")
    print(f"   数据条数: {len(info)}")
except Exception as e:
    print(f"❌ 获取个股信息失败: {e}")

# 测试2: 获取实时行情（全市场）
start = time.time()
try:
    df = ak.stock_zh_a_spot_em()
    print(f"✅ 获取实时行情成功，耗时: {time.time() - start:.2f}秒")
    print(f"   数据条数: {len(df)}")
except Exception as e:
    print(f"❌ 获取实时行情失败: {e}")

# 测试3: 获取业绩报表
start = time.time()
try:
    df = ak.stock_yjbb_em(date='20240930')
    print(f"✅ 获取业绩报表成功，耗时: {time.time() - start:.2f}秒")
    print(f"   数据条数: {len(df)}")
except Exception as e:
    print(f"❌ 获取业绩报表失败: {e}")

print("\n测试完成！")