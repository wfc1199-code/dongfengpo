"""测试AkShare板块相关API"""
import akshare as ak
import pandas as pd

print("=" * 60)
print("测试1: 行业板块实时行情 - stock_board_industry_spot_em")
print("=" * 60)
try:
    df = ak.stock_board_industry_spot_em()
    if df is not None and not df.empty:
        print(f"✅ 成功获取 {len(df)} 个行业板块")
        print("\n前5个板块:")
        print(df.head()[['板块名称', '涨跌幅', '总市值', '换手率']])
    else:
        print("❌ 返回数据为空")
except Exception as e:
    print(f"❌ 失败: {e}")

print("\n" + "=" * 60)
print("测试2: 概念板块实时行情 - stock_board_concept_spot_em")
print("=" * 60)
try:
    df = ak.stock_board_concept_spot_em()
    if df is not None and not df.empty:
        print(f"✅ 成功获取 {len(df)} 个概念板块")
        print("\n前5个板块:")
        print(df.head()[['板块名称', '涨跌幅', '总市值', '换手率']])
    else:
        print("❌ 返回数据为空")
except Exception as e:
    print(f"❌ 失败: {e}")

print("\n" + "=" * 60)
print("测试3: 地域板块实时行情 - stock_board_area_spot_em")
print("=" * 60)
try:
    df = ak.stock_board_area_spot_em()
    if df is not None and not df.empty:
        print(f"✅ 成功获取 {len(df)} 个地域板块")
        print("\n前5个板块:")
        print(df.head()[['板块名称', '涨跌幅', '总市值', '换手率']])
    else:
        print("❌ 返回数据为空")
except Exception as e:
    print(f"❌ 失败: {e}")
