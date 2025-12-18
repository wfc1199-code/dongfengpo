
import akshare as ak
import sys
import pandas as pd

def probe_csi1000_options():
    print("Python executable:", sys.executable)
    print("AkShare version:", ak.__version__)
    
    try:
        # 1. Try to get all option codes capable for "中证1000" or "MO"
        # Using option_cffex_spot_price or similar if available, else try to find list
        # "MO" is the code for CSI 1000 Index Options on CFFEX
        
        print("\n--- Attempting to fetch CFFEX Option Daily (or similar) ---")
        # option_cffex_daily_trade might function for historical
        # option_finance_board might be for current board
        
        # Let's try to search for "MO" related symbols
        # option_current_cffex_spot_price might not exist, but let's check
        
        # A more reliable way: option_risk_indicator_cffex?
        
        # Let's try "option_finance_board" for "中金所" (CFFEX)
        # However, akshare documentation often uses specific function names.
        
        # Commonly used: ak.option_cffex_spot_price(symbol="MO")?
        # Let's inspect potential functions.
        
        print("Checking for 'option_finance_board'...")
        try:
           # Assuming this might fetch finance options
           # But usually 'MO' is handled separately or within option_cffex...
           pass
        except:
           pass

        # Try specific function for CFFEX options
        # ak.option_cffex_daily_trade(date="20241214") ?
        
        # Let's try to get the current list of contracts for MO
        # ak.futures_display_main_sina() includes main futures, check if it has MO
        
        print("\n--- Listing Futures/Options Main Contracts ---")
        try:
             df = ak.futures_display_main_sina()
             mo_contracts = df[df['symbol'].astype(str).str.contains('MO', case=False, na=False)]
             print(f"Found {len(mo_contracts)} MO related contracts in futures_display_main_sina")
             if not mo_contracts.empty:
                 print(mo_contracts.head())
        except Exception as e:
            print(f"Error fetching futures display: {e}")

        # Try to get option chain/quotes using Sina source which is common
        # ak.option_sina_cffex_spot_price(symbol="mo2412") # Example
        
        # We need a valid contract. "MO" + YYMM
        # Assuming 2025 Jan -> MO2501
        contract = "MO2501" 
        print(f"\n--- Attempting to fetch Spot Price for {contract} ---")
        try:
            # Note: akshare often requires specific symbol format
            df = ak.option_sina_cffex_spot_price(symbol=contract)
            if df is not None and not df.empty:
                print("Success! Data sample:")
                print(df.head())
                print("Columns:", df.columns.tolist())
            else:
                print("Returned empty or None")
        except AttributeError:
             print("Function option_sina_cffex_spot_price not found.")
        except Exception as e:
             print(f"Error fetching spot price: {e}")

    except Exception as e:
        print(f"General Error: {e}")

if __name__ == "__main__":
    probe_csi1000_options()
