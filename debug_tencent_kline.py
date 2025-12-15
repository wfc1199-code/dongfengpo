import requests
import os
import json
# Clear proxy
for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(k, None)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/"
}
def test_url(url, label):
    print(f"\nTesting {label}...")
    print(f"URL: {url}")
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        print(f"Status: {resp.status_code}")
        try:
            data = resp.json()
            code = data.get("code")
            msg = data.get("msg")
            print(f"Response Code: {code}, Msg: {msg}")
            if code == 0:
                print("SUCCESS! Data keys:", list(data.get("data", {}).keys()))
                # sample
                stock_data = data.get("data", {}).get("sz000001", {})
                print("Sample keys:", list(stock_data.keys()))
        except:
            print("Response:", resp.text[:200])
    except Exception as e:
        print(f"Error: {e}")
base_fq = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
base_k = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"
# Try variations for 5min
variations = [
    # fqkline
    (base_fq, "param=sz000001,m5,,,320,qfq", "fqkline m5 qfq"),
    (base_fq, "param=sz000001,m5,,,320", "fqkline m5 no-adjust"),
    (base_fq, "param=sz000001,min5,,,320", "fqkline min5"),
    (base_fq, "param=sz000001,5,,,320", "fqkline 5"),
    
    # kline parameters
    (base_k, "param=sz000001,m5,,,320", "kline m5"),
    (base_k, "param=sz000001,m5,,320", "kline m5 (less commas)"),
    (base_k, "param=sz000001,m15,,,320", "kline m15"),
    
    # Baseline check
    (base_fq, "param=sz000001,day,,,320,qfq", "fqkline day (baseline)"),
    
    # Variations based on online examples
    (base_k, "param=sz000001,m5,,320,", "kline m5 4 params"),
    (base_k, "param=sz000001,m5,320", "kline m5 3 params"),
    ("https://web.ifzq.gtimg.cn/appstock/app/mkline/get", "param=sz000001,m5,,320", "mkline/get m5"),
    
    # Try different period codes
    (base_fq, "param=sz000001,m5,,,320,qfq", "fqkline m5 qfq (retry)"),
]
for base, query, label in variations:
    test_url(f"{base}?{query}", label)
