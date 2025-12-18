
import akshare as ak
import pandas as pd

def probe_em():
    print("\n--- Probing ak.option_current_em() ---")
    try:
        # Check signature or just try calling it without args first, or look for clues
        # Usually takes no args or symbol
        df = ak.option_current_em()
        if df is None or df.empty:
            print("Return empty.")
        else:
            print(f"Columns: {df.columns.tolist()}")
            print(df.head(5))
            # Check for CSI 1000 relate names
            print("Searching for '1000' or 'MO' in names/codes...")
            # Column names might differ
            col_name = '名称' if '名称' in df.columns else 'name'
            col_code = '代码' if '代码' in df.columns else 'code'
            
            if col_name in df.columns:
                matches = df[df[col_name].astype(str).str.contains('1000')]
                print(f"Found {len(matches)} matches for '1000' in name.")
                if not matches.empty:
                    print(matches.head())
    except Exception as e:
        print(f"Error probing em: {e}")

def probe_sina_list():
    print("\n--- Probing ak.option_cffex_zz1000_list_sina() ---")
    try:
        # Maybe the 'spot' function is broken but 'list' works and we can loop?
        df = ak.option_cffex_zz1000_list_sina()
        if df is None or df.empty:
            print("Return empty.")
        else:
            print(f"Columns: {df.columns.tolist()}")
            print(df.head(5))
    except Exception as e:
        print(f"Error probing sina list: {e}")

if __name__ == "__main__":
    probe_em()
    probe_sina_list()
