from fastapi import APIRouter, HTTPException
import aiohttp
import logging
from typing import Dict, List, Any, Optional
import os
import asyncio
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/api/anomaly",
    tags=["anomaly"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

# In-memory cache for hot sectors data
_hot_sectors_cache: Dict[str, Any] = {
    "data": None,
    "timestamp": None,
    "ttl_seconds": 900  # 15 minutes default
}

async def fetch_eastmoney_sectors(sector_type: str = "concept", retry_count: int = 3) -> List[Dict]:
    """Fetch sector data from EastMoney with retry mechanism."""
    # 90 = 概念, 90+t:2 = 行业
    fs_param = "m:90" if sector_type == "concept" else "m:90+t:2"
    
    url = 'http://push2.eastmoney.com/api/qt/clist/get'
    params = {
        'pn': '1', 'pz': '50', 'po': '1', 'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2', 'invt': '2', 'fid': 'f3',
        'fs': fs_param,
        'fields': 'f1,f2,f3,f4,f5,f6,f12,f14,f104'
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "http://quote.eastmoney.com/"
    }
    
    # Create session outside retry loop
    timeout = aiohttp.ClientTimeout(total=10)
    connector = aiohttp.TCPConnector(force_close=True)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout, connector=connector, trust_env=False) as session:
            for attempt in range(retry_count):
                try:
                    async with session.get(url, params=params, headers=headers) as response:
                        if response.status == 200:
                            text = await response.text()
                            if not text or text.strip() == "":
                                logger.warning(f"EastMoney {sector_type} API returned empty response (attempt {attempt + 1}/{retry_count})")
                                if attempt < retry_count - 1:
                                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                                    continue
                                return []
                            
                            data = await response.json()
                            if 'data' in data and data['data'] and 'diff' in data['data']:
                                logger.info(f"Successfully fetched {len(data['data']['diff'])} {sector_type} sectors from EastMoney")
                                return data['data']['diff']
                            else:
                                logger.warning(f"EastMoney {sector_type} API returned invalid format (attempt {attempt + 1}/{retry_count})")
                        else:
                            logger.warning(f"EastMoney API returned {response.status} for {sector_type} (attempt {attempt + 1}/{retry_count})")
                        
                        if attempt < retry_count - 1:
                            await asyncio.sleep(1 * (attempt + 1))
                            
                except Exception as e:
                    logger.error(f"Failed to fetch EastMoney sectors ({sector_type}, attempt {attempt + 1}/{retry_count}): {e}")
                    if attempt < retry_count - 1:
                        await asyncio.sleep(1 * (attempt + 1))
    except Exception as e:
        logger.error(f"Failed to create session for {sector_type}: {e}")
    
    return []

@router.get("/hot-sectors")
async def get_hot_sectors(limit: int = 20):
    """Get hot sectors with caching and fallback mechanism."""
    import asyncio
    
    # Check cache first
    cache_valid = False
    if _hot_sectors_cache["data"] and _hot_sectors_cache["timestamp"]:
        cache_age = (datetime.now() - _hot_sectors_cache["timestamp"]).total_seconds()
        if cache_age < _hot_sectors_cache["ttl_seconds"]:
            cache_valid = True
            logger.info(f"Hot sectors cache is valid (age: {cache_age:.0f}s, TTL: {_hot_sectors_cache['ttl_seconds']}s)")
    
    try:
        # Try to use Limit Up Pool for "Continuous Board Heat" (Hot Sectors based on limit-up strength)
        limit_up_sectors = []
        try:
            import datetime as dt
            now = dt.datetime.now()
            
            for i in range(4):
                try_date = now - dt.timedelta(days=i)
                if try_date.weekday() > 4: continue
                date_param = try_date.strftime("%Y%m%d")
                
                url = f"http://push2ex.eastmoney.com/getTopicZtpPool"
                params = {
                    "ut": "7eea3edcaed734bea9cbfc24409ed989",
                    "dpt": "wz.ztzt",
                    "Pageindex": "0",
                    "pagesize": "100",
                    "sort": "fbt:asc",
                    "date": date_param
                }
                headers = {"Referer": "http://quote.eastmoney.com/"}
                
                timeout = aiohttp.ClientTimeout(total=10)
                connector = aiohttp.TCPConnector(force_close=True)
                
                async with aiohttp.ClientSession(timeout=timeout, connector=connector, trust_env=False) as session:
                    async with session.get(url, params=params, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'data' in data and data['data'] and 'pool' in data['data']:
                                pool = data['data']['pool']
                                if pool:
                                    # Aggregate by Industry (hybk)
                                    sector_map = {}
                                    for item in pool:
                                        industry = item.get('hybk', '其他')
                                        if not industry: continue
                                        
                                        if industry not in sector_map:
                                            sector_map[industry] = {"count": 0, "consecutive_sum": 0, "stocks": []}
                                        
                                        sector_map[industry]["count"] += 1
                                        sector_map[industry]["consecutive_sum"] += item.get('lbc', 1)
                                        sector_map[industry]["stocks"].append(item.get('n', ''))
                                    
                                    # Convert to list
                                    for name, stats in sector_map.items():
                                        limit_up_sectors.append({
                                            "sector_name": name,
                                            "avg_change": 10.0, # All are limit up roughly
                                            "stock_count": stats["count"],
                                            "hot_score": stats["consecutive_sum"] * 10 + stats["count"] * 5,
                                            "trend": "up",
                                            "category": "概念",
                                            "description": f"连板{stats['consecutive_sum']}次"
                                        })
                                    break
            
            if limit_up_sectors:
                limit_up_sectors.sort(key=lambda x: x['hot_score'], reverse=True)
                for idx, s in enumerate(limit_up_sectors):
                    s['rank'] = idx + 1
                
                # Update cache
                _hot_sectors_cache["data"] = limit_up_sectors[:limit]
                _hot_sectors_cache["timestamp"] = datetime.now()
                logger.info(f"✅ Successfully fetched {len(limit_up_sectors)} sectors from limit-up pool, cached")
                
                return {
                    "code": 200,
                    "message": "success",
                    "data": {
                        "scan_type": "hot_sectors",
                        "sectors": limit_up_sectors[:limit],
                        "count": len(limit_up_sectors),
                        "data_source": "continuous_board_heat",
                        "cached": False,
                        "cache_time": None
                    }
                }
        except Exception as e:
            logger.warning(f"Failed to get continuous board heat: {e}")
            # Fallback to standard flow below
        
        # Standard Flow (Concept/Industry Fetch) with retry
        logger.info("Fetching hot sectors from EastMoney concept/industry APIs...")
        results = await asyncio.gather(
            fetch_eastmoney_sectors("concept", retry_count=3),
            fetch_eastmoney_sectors("industry", retry_count=3),
            return_exceptions=True
        )
        
        concepts = results[0] if isinstance(results[0], list) else []
        industries = results[1] if isinstance(results[1], list) else []
        
        if isinstance(results[0], Exception):
            logger.error(f"Concept fetch failed: {results[0]}")
        if isinstance(results[1], Exception):
            logger.error(f"Industry fetch failed: {results[1]}")
        
        all_sectors = []
        seen_names = set()

        # Process Concepts
        for sector in concepts:
            name = sector.get('f14', '')
            if not name or name in seen_names:
                continue
            
            change_percent = float(sector.get('f3', 0) or 0)
            f5_val = float(sector.get('f5', 0) or 0)
            hot_score = abs(change_percent) * 10 + (f5_val / 100000 if f5_val > 0 else 0)
            
            all_sectors.append({
                "sector_name": name,
                "avg_change": change_percent,
                "stock_count": int(sector.get('f104', 0) or 0),
                "total_amount": float(sector.get('f6', 0) or 0),
                "hot_score": round(hot_score, 1),
                "trend": "up" if change_percent > 2 else ("stable" if change_percent > -1 else "down"),
                "category": "概念"
            })
            seen_names.add(name)
            
        # Process Industries
        for sector in industries:
            name = sector.get('f14', '')
            if not name or name in seen_names:
                continue
                
            change_percent = float(sector.get('f3', 0) or 0)
            f5_val = float(sector.get('f5', 0) or 0)
            hot_score = abs(change_percent) * 10 + (f5_val / 100000 if f5_val > 0 else 0)
             
            all_sectors.append({
                "sector_name": name,
                "avg_change": change_percent,
                "stock_count": int(sector.get('f104', 0) or 0),
                "total_amount": float(sector.get('f6', 0) or 0),
                "hot_score": round(hot_score, 1),
                "trend": "up" if change_percent > 2 else ("stable" if change_percent > -1 else "down"),
                "category": "行业"
            })
            seen_names.add(name)
        
        # If we got data, update cache and return
        if all_sectors:
            all_sectors.sort(key=lambda x: x['avg_change'], reverse=True)
            result_sectors = all_sectors[:limit]
            
            # Add Rank
            for idx, sector in enumerate(result_sectors):
                sector['rank'] = idx + 1
            
            # Update cache
            _hot_sectors_cache["data"] = result_sectors
            _hot_sectors_cache["timestamp"] = datetime.now()
            logger.info(f"✅ Successfully fetched {len(result_sectors)} sectors from EastMoney, cached")
            
            return {
                "code": 200,
                "message": "success",
                "data": {
                    "scan_type": "hot_sectors",
                    "sectors": result_sectors,
                    "count": len(result_sectors),
                    "data_source": "eastmoney_direct",
                    "cached": False,
                    "cache_time": None
                }
            }
        
        # If no data from APIs, try cache
        logger.warning("⚠️ All hot sectors APIs returned empty data")
        if _hot_sectors_cache["data"]:
            cache_age_minutes = (datetime.now() - _hot_sectors_cache["timestamp"]).total_seconds() / 60
            logger.info(f"📦 Using cached hot sectors data (age: {cache_age_minutes:.1f} minutes)")
            return {
                "code": 200,
                "message": "success",
                "data": {
                    "scan_type": "hot_sectors",
                    "sectors": _hot_sectors_cache["data"],
                    "count": len(_hot_sectors_cache["data"]),
                    "data_source": "cache",
                    "cached": True,
                    "cache_time": _hot_sectors_cache["timestamp"].isoformat()
                }
            }
        
        # No data at all
        logger.error("❌ No hot sectors data available (APIs failed and no cache)")
        return {
            "code": 200,
            "message": "success",
            "data": {
                "scan_type": "hot_sectors",
                "sectors": [],
                "count": 0,
                "data_source": "none",
                "cached": False,
                "cache_time": None,
                "error": "Non-trading hours or API unavailable, no cached data"
            }
        }
            
    except Exception as e:
        logger.error(f"Error in hot_sectors: {e}", exc_info=True)
        
        # Try to return cached data even on exception
        if _hot_sectors_cache["data"]:
            logger.info(f"📦 Exception occurred, returning cached data")
            return {
                "code": 200,
                "message": "success",
                "data": {
                    "scan_type": "hot_sectors",
                    "sectors": _hot_sectors_cache["data"],
                    "count": len(_hot_sectors_cache["data"]),
                    "data_source": "cache_fallback",
                    "cached": True,
                    "cache_time": _hot_sectors_cache["timestamp"].isoformat(),
                    "error": str(e)
                }
            }
        
        raise HTTPException(status_code=500, detail=str(e))

async def fetch_sector_stock_list(sector_code: str, limit: int = 200) -> List[Dict]:
    """Fetch stocks for a given sector code."""
    url = 'http://push2.eastmoney.com/api/qt/clist/get'
    params = {
        'pn': '1', 'pz': str(limit), 'po': '1', 'np': '1',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2', 'invt': '2', 'fid': 'f3',
        'fs': f'b:{sector_code}',
        'fields': 'f12,f14,f2,f3,f4,f5,f6,f8,f15,f16,f17,f18,f10,f9,f20,f21'
    }
    
    timeout = aiohttp.ClientTimeout(total=5)
    connector = aiohttp.TCPConnector(force_close=True)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout, connector=connector, trust_env=False) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'data' in data and data['data'] and 'diff' in data['data']:
                        return data['data']['diff']
    except Exception as e:
        logger.error(f"Failed to fetch stocks for sector {sector_code}: {e}")
    
    return []

@router.get("/sector-stocks/{sector_name}")
async def get_sector_stocks(sector_name: str, limit: int = 200):
    """Get stocks by sector name."""
    import asyncio
    
    def safe_float(value, default=0.0):
        """Safely convert value to float, handling '-' and None."""
        if value is None or value == '' or value == '-':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    try:
        # 1. Fetch all sectors to find the code
        # Ideally this should be cached or we should use a search API
        results = await asyncio.gather(
            fetch_eastmoney_sectors("concept", retry_count=3),
            fetch_eastmoney_sectors("industry", retry_count=3),
            return_exceptions=True
        )
        
        target_code = None
        
        # 1. Exact Match
        for res in results:
            if isinstance(res, list):
                for s in res:
                    if s.get('f14') == sector_name:
                        target_code = s.get('f12')
                        break
            if target_code: break
            
        # 2. Fuzzy Match (if exact failed)
        if not target_code:
            logger.info(f"Exact match failed for '{sector_name}', trying fuzzy match...")
            for res in results:
                if isinstance(res, list):
                    for s in res:
                        name = s.get('f14', '')
                        if sector_name in name or name in sector_name:
                            # Use the one with longer overlap or just the first reasonable one
                            target_code = s.get('f12')
                            logger.info(f"Fuzzy matched: {name} (Code: {target_code})")
                            break
                if target_code: break

        if not target_code:
            concept_count = len(results[0]) if isinstance(results[0], list) else 0
            industry_count = len(results[1]) if isinstance(results[1], list) else 0
            logger.warning(f"Sector '{sector_name}' not found. Scanned {concept_count} concepts, {industry_count} industries.")
            return {
                "code": 404, 
                "message": f"Sector {sector_name} not found. Scanned {concept_count} concepts, {industry_count} industries.", 
                "data": {"stocks": []}
            }
            
        # 2. Fetch stocks
        logger.info(f"Fetching stocks for sector '{sector_name}' (code: {target_code})")
        raw_stocks = await fetch_sector_stock_list(target_code, limit)
        
        if not raw_stocks:
            logger.warning(f"No stocks found for sector '{sector_name}' (code: {target_code})")
            return {
                "code": 200,
                "message": "success",
                "data": {
                    "scan_type": "sector_stocks",
                    "sector_name": sector_name,
                    "stocks": [],
                    "count": 0
                }
            }
        
        # 3. Format with safe conversions
        stocks = []
        for s in raw_stocks:
            stocks.append({
                "stock_code": s.get('f12'),
                "stock_name": s.get('f14'),
                "current_price": safe_float(s.get('f2')),
                "change_percent": safe_float(s.get('f3')),
                "volume": safe_float(s.get('f5')),
                "amount": safe_float(s.get('f6')),
                "market_value": safe_float(s.get('f20')),
                "turnover_rate": safe_float(s.get('f8')),
                "is_leader": False
            })
            
        # Determine leader (safe sorting with safe_float already applied)
        if stocks:
            stocks.sort(key=lambda x: x.get('change_percent', 0), reverse=True)
            if stocks:
                stocks[0]['is_leader'] = True
        
        logger.info(f"Successfully fetched {len(stocks)} stocks for sector '{sector_name}'")
        return {
            "code": 200,
            "message": "success",
            "data": {
                "scan_type": "sector_stocks",
                "sector_name": sector_name,
                "stocks": stocks,
                "count": len(stocks)
            }
        }
    except Exception as e:
        logger.error(f"Error fetching sector stocks for '{sector_name}': {e}", exc_info=True)
        return {"code": 500, "message": str(e), "data": {"stocks": []}}


@router.get("/market-anomaly/scan")
async def scan_market_anomaly(
    anomaly_type: str = "all",
    limit: int = 50
):
    """
    市场异动扫描 - 兼容前端MarketAnomalyScanner组件
    
    从Legacy版本迁移 (backend/main_modular.py:292)
    适配BMAD架构，使用Signal API的数据源
    """
    try:
        # 尝试使用现有的异动检测逻辑
        # 如果strategy-engine可用，优先使用
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 尝试调用strategy-engine的异动检测
                response = await client.get(
                    "http://localhost:8003/api/v2/strategies/anomaly-detection/signals",
                    params={"limit": limit}
                )
                if response.status_code == 200:
                    signals = response.json()
                    # 转换为前端期望的格式
                    stocks = []
                    for signal in signals[:limit]:
                        score = signal.get('confidence', 0) * 100
                        if score >= 80:
                            level, color = "极强", "#ff4444"
                        elif score >= 60:
                            level, color = "强势", "#ff8800"
                        elif score >= 40:
                            level, color = "活跃", "#ffcc00"
                        else:
                            level, color = "普通", "#888888"
                        
                        stocks.append({
                            "code": signal.get('symbol', '').replace('sh', '').replace('sz', ''),
                            "name": signal.get('stock_name', ''),
                            "price": signal.get('current_price', 0),
                            "change": 0,
                            "change_percent": signal.get('change_percent', 0),
                            "volume": signal.get('volume', 0),
                            "amount": signal.get('amount', 0),
                            "turnover_rate": signal.get('turnover_rate', 0),
                            "amplitude": 0,
                            "volume_ratio": 0,
                            "speed_5min": 0,
                            "anomaly_score": score,
                            "anomaly_level": level,
                            "level_color": color,
                            "anomaly_reasons": signal.get('reasons', [])
                        })
                    
                    stats = {
                        "total_count": len(stocks),
                        "extreme_strong": len([s for s in stocks if s['anomaly_score'] >= 80]),
                        "strong": len([s for s in stocks if 60 <= s['anomaly_score'] < 80]),
                        "active": len([s for s in stocks if 40 <= s['anomaly_score'] < 60])
                    }
                    
                    return {"status": "success", "stocks": stocks, "stats": stats}
        except Exception as e:
            logger.debug(f"Strategy-engine unavailable, using fallback: {e}")
        
        # Fallback: 使用现有的anomaly/detect逻辑
        # 使用hot-sectors数据作为基础，转换为异动格式
        
        # 使用hot-sectors数据作为基础，转换为异动格式
        sectors_data = await fetch_eastmoney_sectors("concept", retry_count=2)
        
        stocks = []
        for sector in sectors_data[:limit]:
            # 从板块数据中提取异动信息
            change = float(sector.get('f3', 0))  # 涨跌幅
            if abs(change) > 2:  # 只包含有明显异动的
                score = min(abs(change) * 10, 100)
                if score >= 80:
                    level, color = "极强", "#ff4444"
                elif score >= 60:
                    level, color = "强势", "#ff8800"
                elif score >= 40:
                    level, color = "活跃", "#ffcc00"
                else:
                    level, color = "普通", "#888888"
                
                stocks.append({
                    "code": sector.get('f12', ''),
                    "name": sector.get('f14', ''),
                    "price": float(sector.get('f2', 0)),
                    "change": change,
                    "change_percent": change,
                    "volume": float(sector.get('f5', 0)),
                    "amount": float(sector.get('f6', 0)),
                    "turnover_rate": 0,
                    "amplitude": 0,
                    "volume_ratio": 0,
                    "speed_5min": 0,
                    "anomaly_score": score,
                    "anomaly_level": level,
                    "level_color": color,
                    "anomaly_reasons": [f"板块异动: {change:.2f}%"]
                })
        
        stats = {
            "total_count": len(stocks),
            "extreme_strong": len([s for s in stocks if s['anomaly_score'] >= 80]),
            "strong": len([s for s in stocks if 60 <= s['anomaly_score'] < 80]),
            "active": len([s for s in stocks if 40 <= s['anomaly_score'] < 60])
        }
        
        return {"status": "success", "stocks": stocks, "stats": stats}
        
    except Exception as e:
        logger.error(f"市场异动扫描失败: {e}", exc_info=True)
        return {
            "status": "error",
            "stocks": [],
            "stats": {
                "total_count": 0,
                "extreme_strong": 0,
                "strong": 0,
                "active": 0
            },
            "error": str(e)
        }
