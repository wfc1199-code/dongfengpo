"""Legacy-compatible stock endpoints (read-model / utilities).
Initial migration target: `/api/stocks/search`.
This intentionally avoids importing legacy backend modules; it serves from a
local snapshot file (best-effort) to reduce coupling.
"""
from __future__ import annotations
import json
import os
import logging
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stocks", tags=["stocks"])
def _default_snapshot_path() -> Path:
    # Prefer the repo's shipped snapshot; allow override in deployments.
    rel = os.environ.get("DFP_STOCK_SNAPSHOT_PATH", "backend/data/stock_snapshot.json")
    path = Path(rel)
    # If relative path, try to resolve from project root (2 levels up from services/signal-api)
    if not path.is_absolute():
        # Try current directory first (if running from project root)
        if (Path.cwd() / path).exists():
            return Path.cwd() / path
        # Try from services/signal-api directory (go up 2 levels to project root)
        project_root = Path(__file__).parent.parent.parent.parent.parent
        if (project_root / path).exists():
            return project_root / path
        # Fallback to current directory
        return Path.cwd() / path
    return path
@lru_cache(maxsize=1)
def _load_snapshot() -> Dict[str, Any]:
    path = _default_snapshot_path()
    if not path.is_absolute():
        # Resolve relative to process CWD; in repo/compose runs this is repo root.
        path = Path.cwd() / path
    if not path.exists():
        return {"stocks": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"stocks": {}}
def _normalize_items(snapshot: Dict[str, Any]) -> List[Dict[str, str]]:
    stocks = snapshot.get("stocks")
    items: List[Dict[str, str]] = []
    if isinstance(stocks, dict):
        for symbol, rec in stocks.items():
            if not isinstance(rec, dict):
                continue
            code = str(rec.get("code") or "")
            name = str(rec.get("name") or "")
            if not code and isinstance(symbol, str):
                code = symbol
            items.append({"code": code, "name": name, "symbol": str(symbol)})
    elif isinstance(stocks, list):
        for rec in stocks:
            if not isinstance(rec, dict):
                continue
            items.append({
                "code": str(rec.get("code") or ""),
                "name": str(rec.get("name") or ""),
                "symbol": str(rec.get("symbol") or rec.get("market") or ""),
            })
    return items
def _format_stock_symbol(stock_code: str) -> str:
    stock_code = stock_code.strip()
    if stock_code.startswith(("sh", "sz", "hk")):
        return stock_code
    # Hong Kong: 5 digits
    if len(stock_code) == 5 and stock_code.isdigit():
        return "hk" + stock_code
    # Shanghai: starts with 6
    if stock_code.startswith("6"):
        return "sh" + stock_code
    # default Shenzhen (0/2/3/...)
    return "sz" + stock_code
def _lookup_snapshot_record(symbol: str) -> Dict[str, Any] | None:
    snapshot = _load_snapshot()
    stocks = snapshot.get("stocks")
    if isinstance(stocks, dict):
        rec = stocks.get(symbol)
        if isinstance(rec, dict):
            return rec
    return None
@router.get("/search")
async def search_stocks(
    keyword: str = Query("", min_length=1),
    limit: int = Query(20, ge=1, le=200),
) -> Dict[str, object]:
    """Search stocks by code/name/symbol.
    
    Strategy:
    1. First try local snapshot (fast)
    2. If no results or less than 3, fallback to online EastMoney API
    
    Response shape: `{ "stocks": [...] }`.
    """
    q = keyword.strip()
    if not q:
        return {"stocks": [], "total": 0}
    
    # Try local snapshot first
    snapshot = _load_snapshot()
    items = _normalize_items(snapshot)
    q_lower = q.lower()
    
    def score(it: Dict[str, str]) -> int:
        code = it.get("code", "").lower()
        name = it.get("name", "").lower()
        sym = it.get("symbol", "").lower()
        if code == q_lower or sym == q_lower:
            return 100
        if q_lower and (code.startswith(q_lower) or sym.startswith(q_lower)):
            return 80
        if q_lower and name.startswith(q_lower):
            return 70
        if q_lower and (q_lower in code or q_lower in sym):
            return 60
        if q_lower and q_lower in name:
            return 50
        return 0
    
    matched = [it for it in items if score(it) > 0]
    matched.sort(key=lambda it: (-score(it), it.get("code", "")))
    local_results = [{"code": it.get("code", ""), "name": it.get("name", "")} for it in matched[:limit]]
    
    # If local results are sufficient, return them
    if len(local_results) >= 3:
        return {"stocks": local_results, "total": len(matched)}
    
    # Fallback to online search (EastMoney)
    try:
        online_results = await _search_online(q, limit)
        if online_results:
            # Merge: local first, then online (deduplicated)
            seen_codes = {r["code"] for r in local_results}
            for r in online_results:
                if r["code"] not in seen_codes:
                    local_results.append(r)
                    seen_codes.add(r["code"])
                    if len(local_results) >= limit:
                        break
            return {"stocks": local_results[:limit], "total": len(local_results)}
    except Exception as e:
        logger.warning(f"Online search failed: {e}")
    
    return {"stocks": local_results, "total": len(matched)}


async def _search_online(keyword: str, limit: int = 20) -> List[Dict[str, str]]:
    """Search stocks using EastMoney online API."""
    url = "https://searchapi.eastmoney.com/api/suggest/get"
    params = {
        "input": keyword,
        "type": "14",  # 股票搜索
        "token": "D43BF722C8E33BDC906FB84D85E326E8",
        "count": str(limit)
    }
    
    # 使用 requests 同步请求，增加超时和重试
    import requests
    for attempt in range(2):  # 最多重试2次
        try:
            response = requests.get(url, params=params, timeout=10)  # 增加到10秒
            if response.status_code == 200:
                data = response.json()
                results = []
                
                quotes = data.get("QuotationCodeTable", {}).get("Data", [])
                for item in quotes:
                    code = item.get("Code", "")
                    name = item.get("Name", "")
                    market = str(item.get("MktNum", ""))
                    
                    # Only include A-shares (沪深): 1=沪, 0=深
                    if market in ["1", "0"]:
                        results.append({
                            "code": code,
                            "name": name
                        })
                
                logger.info(f"✅ 在线搜索 '{keyword}' 返回 {len(results)} 结果")
                return results
        except requests.exceptions.Timeout:
            logger.warning(f"在线搜索超时 (尝试 {attempt + 1}/2)")
            continue
        except Exception as e:
            logger.warning(f"EastMoney search API failed: {e}")
            break
    
    return []


@router.get("/{stock_code}/realtime")
async def get_realtime(stock_code: str) -> Dict[str, object]:
    """Realtime endpoint.
    Shape: { code, data, timestamp }.
    Tries to use real-time data from pipeline, falls back to snapshot.
    """
    from ..data.pipeline_client import get_pipeline_client
    symbol = _format_stock_symbol(stock_code)
    # Try to get real-time data from pipeline
    try:
        client = await get_pipeline_client()
        if client.is_connected():
            features = await client.get_latest_features(symbol)
            if features:
                # Use real-time data from pipeline
                return {
                    "code": symbol,
                    "data": features,
                    "timestamp": features.get("timestamp") or datetime.utcnow().isoformat(),
                    "source": "pipeline",
                }
    except Exception as e:
        # Log but don't fail - fall back to snapshot
        import logging
        logging.getLogger(__name__).debug(f"Pipeline data unavailable: {e}")
    # Fallback to snapshot data
    rec = _lookup_snapshot_record(symbol)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Stock not found: {stock_code}")
    return {
        "code": symbol,
        "data": rec,
        "timestamp": rec.get("update_time"),
        "source": "snapshot",
    }
def _iter_trading_minutes() -> List[str]:
    times: List[str] = []
    # 9:30-11:30 (inclusive of 11:30) => 121 points
    t = datetime(2000, 1, 1, 9, 30)
    end = datetime(2000, 1, 1, 11, 30)
    while t <= end:
        times.append(t.strftime("%H:%M"))
        t += timedelta(minutes=1)
    # 13:00-15:00 (inclusive) => 121 points
    t = datetime(2000, 1, 1, 13, 0)
    end = datetime(2000, 1, 1, 15, 0)
    while t <= end:
        times.append(t.strftime("%H:%M"))
        t += timedelta(minutes=1)
    # Keep 241 points like common A-share timeshare (some systems use 241)
    if len(times) > 241:
        times = times[:241]
    return times
@router.get("/{stock_code}/minute")
async def get_minute(stock_code: str) -> Dict[str, object]:
    """获取分时数据 - 使用完整数据源链（完全独立于原始版本）
    
    数据源优先级: 东方财富 -> 腾讯 -> AkShare -> 快照
    """
    from ..data.data_sources import get_stock_data_manager
    symbol = _format_stock_symbol(stock_code)
    
    # 尝试从真实数据源链获取
    try:
        data_manager = get_stock_data_manager()
        result = await data_manager.get_minute_data(stock_code)
        
        if result and result.get("minute_data"):
            return {
                "code": stock_code,
                "name": result.get("name", ""),
                "minute_data": result["minute_data"],
                "yesterday_close": result.get("yesterday_close"),
                "timestamp": datetime.utcnow().isoformat(),
                "is_realtime": True,
                "notice": None,
                "source": result.get("data_source", "api"),
            }
    except Exception as e:
        # 日志记录失败，继续使用快照回退
        logger.error(f"真实数据源获取分时数据失败: {stock_code} -> {e}", exc_info=True)
    
    # Fallback to snapshot - 所有数据源失败时回退
    rec = _lookup_snapshot_record(symbol)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Stock not found: {stock_code}")
    price = float(rec.get("current_price") or rec.get("price") or 0.0)
    yesterday_close = rec.get("yesterday_close")
    total_volume = float(rec.get("volume") or rec.get("volume_sum") or 0.0) if rec else 0.0
    times = _iter_trading_minutes()
    per_volume = int(total_volume / max(len(times), 1)) if total_volume else 0
    minute_data = [{"time": t, "price": price, "avg_price": price, "volume": per_volume} for t in times]
    return {
        "code": stock_code,
        "name": rec.get("name", ""),
        "minute_data": minute_data,
        "yesterday_close": yesterday_close,
        "timestamp": datetime.utcnow().isoformat(),
        "is_realtime": False,
        "notice": "使用快照数据（所有实时数据源暂不可用）",
        "source": "snapshot",
    }
@router.get("/{stock_code}/timeshare")
async def get_timeshare(stock_code: str) -> Dict[str, object]:
    """Alias for minute."""
    return await get_minute(stock_code)
@router.get("/{stock_code}/kline")
async def get_kline(
    stock_code: str,
    period: str = Query("daily"),
    limit: int = Query(100, ge=1, le=500),
) -> Dict[str, object]:
    """获取K线数据 - 使用完整数据源链（完全独立于原始版本）
    
    数据源优先级: 东方财富 -> 腾讯 -> AkShare -> 快照
    """
    from ..data.data_sources import get_stock_data_manager
    symbol = _format_stock_symbol(stock_code)
    
    # 尝试从真实数据源链获取
    try:
        data_manager = get_stock_data_manager()
        result = await data_manager.get_kline_data(stock_code, period, limit)
        
        if result and result.get("klines"):
            return {
                "code": stock_code,
                "name": result.get("name", ""),
                "period": period,
                "klines": result["klines"],
                "timestamp": datetime.utcnow().isoformat(),
                "yesterday_close": result.get("yesterday_close"),
                "source": result.get("data_source", "api"),
            }
    except Exception as e:
        # 日志记录失败，继续使用快照回退
        logger.error(f"真实数据源获取K线数据失败: {stock_code} (period={period}) -> {e}", exc_info=True)
    
    # Fallback to snapshot - 所有数据源失败时回退
    rec = _lookup_snapshot_record(symbol)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Stock not found: {stock_code}")
    close = float(rec.get("current_price") or 0.0)
    open_p = float(rec.get("open_price") or close)
    high = float(rec.get("high_price") or max(open_p, close))
    low = float(rec.get("low_price") or min(open_p, close))
    volume = float(rec.get("volume") or 0.0)
    # Base date from snapshot update_time if available
    update_time = rec.get("update_time")
    try:
        base_dt = datetime.fromisoformat(str(update_time))
    except Exception:
        base_dt = datetime.utcnow()
    count = min(limit, 200)
    klines: List[Dict[str, object]] = []
    for i in range(count):
        d = (base_dt - timedelta(days=i)).date().isoformat()
        klines.append(
            {
                "date": d,
                "open": open_p,
                "close": close,
                "high": high,
                "low": low,
                "volume": volume,
            }
        )
    return {
        "code": stock_code,
        "name": rec.get("name", ""),
        "period": period,
        "klines": list(reversed(klines)),
        "timestamp": datetime.utcnow().isoformat(),
        "yesterday_close": rec.get("yesterday_close"),
        "source": "snapshot",
        "notice": "使用快照数据（所有实时数据源暂不可用）",
    }
@router.get("/{stock_code}/transactions")
async def get_stock_transactions(
    stock_code: str,
    start_time: str = Query(..., description="开始时间 HH:MM:SS"),
    end_time: str = Query(..., description="结束时间 HH:MM:SS"),
) -> Dict[str, Any]:
    """Get transaction details for a stock (alias for /api/transactions/{stockCode}/details).
    
    This endpoint is an alias that redirects to the transactions router for consistency.
    """
    from ..routers.transactions import get_transaction_details
    return await get_transaction_details(stock_code, start_time, end_time)
@router.get("/{stock_code}/behavior/analysis")
async def behavior_analysis(stock_code: str) -> Dict[str, object]:
    """Minimal behavior analysis for UI usage."""
    symbol = _format_stock_symbol(stock_code)
    rec = _lookup_snapshot_record(symbol)
    if not rec:
        # Return 200 to keep UI resilient
        return {
            "behavior": "unknown",
            "confidence": 0,
            "alert_level": "low",
            "suggestions": [],
            "signals": [],
        }
    change_percent = float(rec.get("change_percent") or 0.0)
    turnover_rate = float(rec.get("turnover_rate") or 0.0)
    if change_percent > 5 and turnover_rate > 10:
        behavior = "shipping"
        confidence = 0.7
        alert_level = "high"
    elif change_percent > 3 and turnover_rate < 5:
        behavior = "washing"
        confidence = 0.6
        alert_level = "opportunity"
    elif change_percent < -3:
        behavior = "shipping"
        confidence = 0.5
        alert_level = "high"
    else:
        behavior = "neutral"
        confidence = 0.4
        alert_level = "low"
    signals: List[Dict[str, str]] = []
    if change_percent > 5:
        signals.append({"type": "price", "signal": "大涨", "meaning": f"涨幅达到{change_percent:.1f}%", "strength": "strong"})
    if turnover_rate > 10:
        signals.append({"type": "volume", "signal": "放量", "meaning": f"换手率{turnover_rate:.1f}%", "strength": "strong"})
    suggestions: List[Dict[str, object]] = []
    if behavior == "shipping":
        suggestions.append({"action": "观望", "reason": "成交活跃但需警惕出货", "confidence": confidence, "risk_level": "高"})
    elif behavior == "washing":
        suggestions.append({"action": "关注", "reason": "可能存在洗盘机会", "confidence": confidence, "risk_level": "中"})
    return {
        "behavior": behavior,
        "confidence": confidence,
        "alert_level": alert_level,
        "suggestions": suggestions,
        "signals": signals,
        "volume_pattern": {
            "volume_ratio": 1.0,
            "is_heavy_volume": turnover_rate > 10,
            "is_shrinking_volume": turnover_rate < 2,
            "divergence": 0,
            "has_divergence": False,
        },
        "price_pattern": {
            "volatility": abs(change_percent),
            "rapid_drops": 1 if change_percent < -3 else 0,
            "slow_rises": 1 if 0 < change_percent < 3 else 0,
            "tail_movement": "unknown",
            "pattern": behavior,
        },
    }