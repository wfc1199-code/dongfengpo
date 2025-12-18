
import akshare as ak
import pandas as pd

try:
    print("Fetching CSI 1000 options (MO) from ak.option_cffex_zz1000_spot_sina()...")
    df = ak.option_cffex_zz1000_spot_sina()
    
    if df is None or df.empty:
        print("DataFrame is empty.")
    else:
        print(f"Columns: {df.columns.tolist()}")
        print(f"Total rows: {len(df)}")
        
        # Check for date-like columns or contract names to infer dates
        print("\n--- Sample contracts (Call) ---")
        if '看涨合约-标识' in df.columns:
            print(df[['看涨合约-标识', '看涨合约-最新价']].head(10))
            # Extract distinct years/months from contract codes
            codes = df['看涨合约-标识'].astype(str).tolist()
            years = set()
            for code in codes:
                # Assuming format mo2208...
                if code.lower().startswith('mo') and len(code) >= 6:
                    years.add(code[2:4])
            print(f"\nDistinct years found in codes (2-digit): {sorted(list(years))}")

        print("\n--- Sample contracts (Put) ---")
        if '看跌合约-标识' in df.columns:
            print(df[['看跌合约-标识', '看跌合约-最新价']].head(10))

except Exception as e:
    print(f"Error: {e}")
