
import aiohttp
import asyncio

async def fetch_sectors():
    # 1. Get Concept Sectors
    url = 'http://push2.eastmoney.com/api/qt/clist/get'
    params = {
        'pn': '1', 'pz': '1000', 'po': '1', 'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2', 'invt': '2', 'fid': 'f3',
        'fs': 'm:90+t:2+f:!50', # Industry? Or m:90 for concepts
        'fields': 'f12,f14'
    }
    
    print("Fetching sectors...")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            # print(data)
            if 'data' in data and 'diff' in data['data']:
                return data['data']['diff']
    return []

async def fetch_stocks(code):
    # Fetch stocks for sector code
    url = 'http://push2.eastmoney.com/api/qt/clist/get'
    # fs param for block usually needs specific format.
    # For industry: m:90+t:2+f:!50 is list of industries.
    # Stocks in industry: b:{code}
    
    params = {
        'pn': '1', 'pz': '20', 'po': '1', 'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2', 'invt': '2', 'fid': 'f3',
        'fs': f'b:{code}',
        'fields': 'f12,f14,f2,f3'
    }
    
    print(f"Fetching stocks for {code}...")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            if 'data' in data and 'diff' in data['data']:
                return data['data']['diff']
            else:
                print("No data found, raw:", data)
    return []

async def main():
    sectors = await fetch_sectors()
    target = "半导体"
    code = None
    for s in sectors:
        if s['f14'] == target:
            code = s['f12']
            print(f"Found {target}: {code}")
            break
            
    if not code and sectors:
        # Pick random
        s = sectors[0]
        code = s['f12']
        print(f"Picking random {s['f14']}: {code}")
        
    if code:
        stocks = await fetch_stocks(code)
        print(f"Stocks in {code}: {len(stocks)}")
        print(stocks[:3])

if __name__ == "__main__":
    asyncio.run(main())
