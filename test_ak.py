
import akshare as ak
import datetime

try:
    today = datetime.datetime.now().strftime("%Y%m%d")
    # Try Friday if today is Sunday
    date = "20251212"
    print(f"Fetching ZT pool for {date}...")
    df = ak.stock_zt_pool_em(date=date)
    print("Columns:", df.columns)
    print("First row:", df.iloc[0].to_dict())
except Exception as e:
    print(f"Error: {e}")
