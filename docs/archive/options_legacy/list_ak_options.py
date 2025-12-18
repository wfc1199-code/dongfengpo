
import akshare as ak

print("Searching for option related functions in akshare...")
for attr in dir(ak):
    if 'option' in attr:
        print(attr)
