"""测试真实板块数据"""
import akshare as ak
import pandas as pd

print("=" * 70)
print("测试1: 概念板块实时行情 - stock_board_concept_spot_em")
print("=" * 70)
try:
    df = ak.stock_board_concept_spot_em()
    if df is not None and not df.empty:
        print(f"✅ 成功获取 {len(df)} 个概念板块")
        print(f"\n列名: {list(df.columns)}")
        print("\n涨幅前10的概念板块:")
        df_sorted = df.sort_values('涨跌幅', ascending=False)
        print(df_sorted.head(10)[['板块名称', '涨跌幅', '总市值', '换手率', '上涨家数', '下跌家数', '领涨股票']])
    else:
        print("❌ 返回数据为空")
except Exception as e:
    print(f"❌ 失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("测试2: 行业板块实时行情 - stock_board_industry_spot_em")
print("=" * 70)
try:
    df = ak.stock_board_industry_spot_em()
    if df is not None and not df.empty:
        print(f"✅ 成功获取 {len(df)} 个行业板块")
        print(f"\n列名: {list(df.columns)}")
        print("\n涨幅前10的行业板块:")
        df_sorted = df.sort_values('涨跌幅', ascending=False)
        print(df_sorted.head(10)[['板块名称', '涨跌幅', '总市值', '换手率', '上涨家数', '下跌家数', '领涨股票']])
    else:
        print("❌ 返回数据为空")
except Exception as e:
    print(f"❌ 失败: {e}")
    import traceback
    traceback.print_exc()
