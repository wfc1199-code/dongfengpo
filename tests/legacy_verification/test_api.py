#!/usr/bin/env python3
import requests
import json
import time

def test_minute_api(stock_code):
    """测试分时数据API"""
    url = f"http://localhost:9000/api/stocks/{stock_code}/minute"
    
    print(f"测试API: {url}")
    start_time = time.time()
    
    try:
        response = requests.get(url, timeout=10)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if 'minute_data' in data:
                print(f"✅ 成功获取数据，耗时: {elapsed:.2f}秒")
                print(f"  股票代码: {data.get('code')}")
                print(f"  股票名称: {data.get('name')}")
                print(f"  数据点数: {len(data['minute_data'])}")
                if data['minute_data']:
                    first = data['minute_data'][0]
                    last = data['minute_data'][-1]
                    print(f"  第一个数据点: {first['time']} - {first['price']}")
                    print(f"  最后数据点: {last['time']} - {last['price']}")
            else:
                print(f"⚠️ 返回数据格式错误: {data}")
        else:
            print(f"❌ 请求失败: HTTP {response.status_code}")
            print(f"  响应内容: {response.text}")
            
    except requests.Timeout:
        print(f"❌ 请求超时（10秒）")
    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    # 测试A股
    print("=" * 50)
    test_minute_api("sz000001")
    
    print("\n" + "=" * 50)
    # 测试港股
    test_minute_api("hk02228")