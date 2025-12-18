
import akshare as ak

print("Fetching CFFEX ZZ1000 option list from Sina...")
try:
    # returns dict?
    data = ak.option_cffex_zz1000_list_sina()
    print(f"Type: {type(data)}")
    print(f"Data: {data}")
except Exception as e:
    print(f"Error: {e}")
