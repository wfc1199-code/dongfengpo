
import os
import socket
import requests
import json

# Clear proxy
for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(k, None)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/"
}

def check_domain(domain):
    print(f"\nChecking {domain}...")
    try:
        ip = socket.gethostbyname(domain)
        print(f"DNS Resolved: {ip}")
        return True
    except Exception as e:
        print(f"DNS Failed: {e}")
        return False

def check_url(url, name):
    print(f"\nTesting {name}...")
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type')}")
        print("Preview:", resp.text[:100])
    except Exception as e:
        print(f"Request Failed: {e}")

# 1. Check Tencent
if check_domain("web.ifzq.gtimg.cn"):
    # Try different formats
    print("Trying format 1: param=sz000001")
    check_url("https://web.ifzq.gtimg.cn/appstock/app/minute/query?code=sz000001", "Tencent Minute (code=)")
    
    print("Trying format 2: param=sz000001")
    check_url("https://web.ifzq.gtimg.cn/appstock/app/minute/query?param=sz000001", "Tencent Minute (param=)")
    
    # K-line test
    print("Trying K-line...")
    check_url("https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sz000001,day,,,100,qfq", "Tencent K-line (Daily)")
    
    # Intraday 5min tests
    print("Trying 5min variations...")
    check_url("https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sz000001,m5,,,100", "Tencent 5min (No qfq)")
    print("Trying mkline (HTTP)...")
    check_url("http://web.ifzq.gtimg.cn/appstock/app/kline/mkline?param=sz000001,m5,,100", "Tencent 5min (mkline HTTP)")
    # Format might be: code,period,start,end,count,info
    # Try different param order or values

# 2. Check EastMoney
if check_domain("push2his.eastmoney.com"):
    # 5min K-line URL
    kline_url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=0.000001&fields1=f1&fields2=f51&klt=5&fqt=1&lmt=10&end=20500101"
    check_url(kline_url, "EastMoney 5min K-line")
