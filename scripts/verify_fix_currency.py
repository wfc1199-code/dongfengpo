
import asyncio
import sys
import os

# Ensure project root is in path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'services/signal-api'))

from signal_api.data.csi1000_option_source import CSI1000OptionDataSource

async def verify_fix():
    print("Verifying CSI 1000 Option Data Currency Fix...")
    source = CSI1000OptionDataSource()
    
    try:
        print("Fetching spot prices...")
        data = await source.get_spot_prices()
        
        print(f"Total contracts fetched: {len(data)}")
        
        if not data:
            print("Failed: No data returned.")
            return

        # Check for years present in the codes
        years = set()
        for item in data:
            code = item['code'] # e.g. mo2512C...
            if code.lower().startswith('mo') and len(code) >= 6:
                years.add(code[2:4])
        
        print(f"Distinct years found in codes (YY): {sorted(list(years))}")
        
        expected_years = ['25', '26'] # Expecting 2025, 2026 data
        has_expected = any(y in years for y in expected_years)
        
        if has_expected:
            print("SUCCESS: Found expected future years in data.")
        else:
            print("FAILURE: Only found old years (likely 22). Fix did not work.")

        # Print sample
        print("\nSample Data (first 3):")
        for item in data[:3]:
            print(item)

    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    asyncio.run(verify_fix())
