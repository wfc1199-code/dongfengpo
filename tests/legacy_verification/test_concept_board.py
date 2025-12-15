"""测试概念板块API"""
import akshare as ak

print("测试概念板块涨幅榜...")
try:
    df = ak.stock_board_concept_em()
    if df is not None and not df.empty:
        print(f"✅ 成功! 共 {len(df)} 个概念板块")
        print(f"列名: {list(df.columns)}")
        print("\n前10个板块:")
        print(df.head(10)[['板块名称', '板块代码', '最新价', '涨跌幅']])
    else:
        print("❌ 数据为空")
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
