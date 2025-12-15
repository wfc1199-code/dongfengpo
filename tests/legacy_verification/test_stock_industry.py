"""测试获取股票行业信息"""
import akshare as ak

print("测试获取个股行业信息...")
print("=" * 60)

# 先获取几只热门股票
try:
    df_hot = ak.stock_hot_rank_em()
    print(f"✅ 获取到 {len(df_hot)} 只热门股票")
    
    # 取前3只测试
    for i in range(min(3, len(df_hot))):
        code = str(df_hot.iloc[i]['代码']).replace('SH', '').replace('SZ', '')
        name = df_hot.iloc[i]['股票名称']
        
        print(f"\n股票: {code} {name}")
        
        # 尝试获取个股信息 - 东财个股信息
        try:
            info = ak.stock_individual_info_em(symbol=code)
            print(f"  个股信息列名: {list(info.columns) if hasattr(info, 'columns') else 'N/A'}")
            if hasattr(info, 'columns') and '行业' in info.columns:
                industry = info[info['item'] == '行业']['value'].values[0] if '行业' in info['item'].values else 'N/A'
                print(f"  行业: {industry}")
        except Exception as e:
            print(f"  ❌ 获取个股信息失败: {e}")
            
except Exception as e:
    print(f"❌ 获取热门股票失败: {e}")
