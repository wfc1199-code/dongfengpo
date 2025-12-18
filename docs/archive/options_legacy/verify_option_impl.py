
import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/../services/signal-api"))

from signal_api.data.csi1000_option_source import CSI1000OptionDataSource

async def verify_csi1000():
    print("=" * 60)
    print("Verifying CSI 1000 Option Implementation")
    print("=" * 60)
    
    source = CSI1000OptionDataSource()
    
    # 1. Test Real-time Quotes
    print("\n[1] Testing get_spot_prices()...")
    try:
        quotes = await source.get_spot_prices()
        print(f"  Result: {len(quotes)} contracts found")
        if quotes:
            print(f"  Sample: {quotes[0]}")
    except Exception as e:
        print(f"  Error: {e}")
        
    # 2. Test Contract Logic (Validation)
    if quotes:
        sample_code = quotes[0]['code']
        print(f"\n[2] Testing get_daily_kline('{sample_code}')...")
        try:
            klines = await source.get_daily_kline(sample_code)
            print(f"  Result: {len(klines)} bars found")
            if klines:
                print(f"  Sample: {klines[-1]}")
        except Exception as e:
            print(f"  Error: {e}")
            
    # 3. Test Volatility Index
    print("\n[3] Testing get_volatility_index()...")
    try:
        vix = await source.get_volatility_index()
        print(f"  Result: {len(vix)} bars found")
        if vix:
            print(f"  Sample: {vix[-1]}")
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_csi1000())
