#!/usr/bin/env python3
"""
列出所有有持久化分钟线数据的股票
"""

from pathlib import Path

def list_valid_stocks():
    """列出所有有parquet数据的股票"""
    data_dir = Path(__file__).parent.parent / "quant_data" / "market_data"
    
    if not data_dir.exists():
        print(f"❌ 数据目录不存在: {data_dir}")
        return []
    
    parquet_files = sorted(data_dir.glob("*.parquet"))
    
    if not parquet_files:
        print(f"❌ 未找到parquet文件")
        return []
    
    print(f"✅ 找到 {len(parquet_files)} 个股票数据文件")
    print()
    
    # 打印前20个
    print("📋 有数据的股票代码 (前20个):")
    print("-" * 60)
    
    valid_symbols = []
    for i, file in enumerate(parquet_files[:20], 1):
        # 000001.SZ.parquet -> 000001
        symbol = file.stem.split('.')[0]
        valid_symbols.append(symbol)
        
        # 每行5个
        if i % 5 == 0:
            print()
        print(f"{symbol:8s}", end="  ")
    
    print()
    print("-" * 60)
    print(f"\n💡 建议在回测脚本中使用这些股票代码")
    
    # 返回所有股票代码
    all_symbols = [file.stem.split('.')[0] for file in parquet_files]
    
    print(f"\n📊 统计:")
    print(f"   - 总数: {len(all_symbols)}")
    print(f"   - 上交所(6开头): {len([s for s in all_symbols if s.startswith('6')])}")
    print(f"   - 深交所(0/3开头): {len([s for s in all_symbols if s[0] in '03'])}")
    
    return all_symbols

if __name__ == "__main__":
    symbols = list_valid_stocks()
    
    # 保存到文件供其他脚本使用
    if symbols:
        output_file = Path(__file__).parent.parent / "valid_stocks.txt"
        with open(output_file, 'w') as f:
            for symbol in symbols:
                f.write(f"{symbol}\n")
        print(f"\n💾 完整列表已保存到: {output_file.name}")
