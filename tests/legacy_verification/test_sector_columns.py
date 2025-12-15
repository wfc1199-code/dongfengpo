"""快速测试板块API列名"""
import akshare as ak

print("测试行业板块API列名...")
try:
    df = ak.stock_board_industry_spot_em()
    if df is not None and not df.empty:
        print(f"✅ 成功! 共 {len(df)} 个板块")
        print(f"列名: {list(df.columns)}")
        print("\n示例数据:")
        print(df.head(3).to_string())
    else:
        print("❌ 数据为空")
except Exception as e:
    print(f"❌ 错误: {e}")
