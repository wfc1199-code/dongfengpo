
import os
import sys

# Clear proxy vars
for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(k, None)

try:
    import akshare as ak
    print(f"AkShare version: {ak.__version__}")
    
    print("Fetching 5min data for 000001...")
    df = ak.stock_zh_a_hist_min_em(symbol="000001", period="5", adjust="qfq")
    print("Success!")
    print(df.head())
    print(f"Columns: {df.columns.tolist()}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
