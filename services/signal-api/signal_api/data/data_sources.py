"""
股票数据源模块 - Signal-API
提供东方财富、腾讯、AkShare等多数据源支持
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime, time as dt_time, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class StockDataSource(ABC):
    """股票数据源抽象基类"""
    
    @abstractmethod
    async def get_minute_data(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取分时数据"""
        pass
    
    @abstractmethod
    async def get_kline_data(self, stock_code: str, period: str, limit: int) -> Optional[Dict[str, Any]]:
        """获取K线数据"""
        pass


class EastMoneyDataSource(StockDataSource):
    """东方财富数据源 (主数据源)"""
    
    TRENDS_URL = "https://push2his.eastmoney.com/api/qt/stock/trends2/get"
    KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    
    # K线周期映射
    PERIOD_MAP = {
        "1min": 1, "5min": 5, "15min": 15, "30min": 30, "60min": 60,
        "daily": 101, "weekly": 102, "monthly": 103
    }
    
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self._last_request_time: Optional[float] = None
        self._min_interval = 0.1  # 100ms 限流
    
    async def _rate_limit(self) -> None:
        """简单限流"""
        if self._last_request_time:
            elapsed = asyncio.get_event_loop().time() - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()
    
    def _format_secid(self, stock_code: str) -> str:
        """格式化为东方财富 secid 格式"""
        clean_code = stock_code.replace("sh", "").replace("sz", "").replace("hk", "")
        
        if stock_code.startswith("sh"):
            return f"1.{clean_code}"
        elif stock_code.startswith("sz"):
            return f"0.{clean_code}"
        elif stock_code.startswith("hk"):
            return f"116.{clean_code}"
        elif clean_code.startswith("6"):
            return f"1.{clean_code}"
        elif clean_code.startswith(("0", "3")):
            return f"0.{clean_code}"
        else:
            return f"0.{clean_code}"
    
    async def get_minute_data(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取分时数据"""
        await self._rate_limit()
        
        # 清除代理环境变量
        for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
            os.environ.pop(k, None)
        
        secid = self._format_secid(stock_code)
        clean_code = stock_code.replace("sh", "").replace("sz", "").replace("hk", "")
        
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
            "iscr": "0",
            "ndays": "1"
        }
        
        # 添加浏览器User-Agent避免被拒绝
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://quote.eastmoney.com/"
        }
        
        # 禁用代理的连接器
        connector = aiohttp.TCPConnector(ssl=False)
        
        try:
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                async with session.get(
                    self.TRENDS_URL, 
                    params=params, 
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"东方财富分时API返回 {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if data.get("rc") != 0 or not data.get("data"):
                        logger.warning(f"东方财富分时API返回错误: {data.get('rc')}")
                        return None
                    
                    api_data = data["data"]
                    stock_name = api_data.get("name", f"股票{clean_code}")
                    preclose = float(api_data.get("preClose", 0))
                    trends = api_data.get("trends", [])
                    
                    if not trends:
                        logger.warning(f"东方财富分时数据为空: {stock_code}")
                        return None
                    
                    minute_data = []
                    for trend in trends:
                        parts = trend.split(",")
                        if len(parts) >= 8:
                            datetime_str = parts[0]  # 格式: 2024-01-01 09:30
                            price = float(parts[2])  # 收盘价
                            volume = int(parts[5])   # 成交量
                            amount = float(parts[6]) # 成交额
                            avg_price = float(parts[7])  # 均价
                            
                            # 提取时间 HH:MM
                            time_str = datetime_str.split(" ")[1] if " " in datetime_str else datetime_str[-5:]
                            
                            minute_data.append({
                                "time": time_str,
                                "price": price,
                                "volume": volume,
                                "amount": amount,
                                "avg_price": avg_price
                            })
                    
                    if minute_data:
                        logger.info(f"✅ 东方财富获取分时数据成功: {clean_code} - {len(minute_data)}条")
                        return {
                            "code": clean_code,
                            "name": stock_name,
                            "minute_data": minute_data,
                            "yesterday_close": preclose,
                            "data_source": "eastmoney"
                        }
                    
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"东方财富分时API超时: {stock_code}")
            return None
        except Exception as e:
            logger.warning(f"东方财富分时API异常: {stock_code} -> {e}")
            return None
    
    async def get_kline_data(self, stock_code: str, period: str = "daily", limit: int = 100) -> Optional[Dict[str, Any]]:
        """获取K线数据"""
        await self._rate_limit()
        
        # 清除代理环境变量
        for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
            os.environ.pop(k, None)
        
        secid = self._format_secid(stock_code)
        clean_code = stock_code.replace("sh", "").replace("sz", "").replace("hk", "")
        klt = self.PERIOD_MAP.get(period, 101)
        
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": klt,
            "fqt": 1,  # 前复权
            "lmt": limit + 1,  # 多请求一条用于获取昨收
            "end": "20500101"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://quote.eastmoney.com/"
        }
        connector = aiohttp.TCPConnector(ssl=False)
        
        try:
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                async with session.get(
                    self.KLINE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"东方财富K线API返回 {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if data.get("rc") != 0 or not data.get("data"):
                        logger.warning(f"东方财富K线API返回错误: {data.get('rc')}")
                        return None
                    
                    api_data = data["data"]
                    stock_name = api_data.get("name", f"股票{clean_code}")
                    klines_raw = api_data.get("klines", [])
                    
                    if not klines_raw:
                        logger.warning(f"东方财富K线数据为空: {stock_code}")
                        return None
                    
                    klines = []
                    yesterday_close = None
                    
                    for i, kline in enumerate(klines_raw):
                        parts = kline.split(",")
                        if len(parts) >= 7:
                            kline_data = {
                                "date": parts[0],
                                "open": float(parts[1]),
                                "close": float(parts[2]),
                                "high": float(parts[3]),
                                "low": float(parts[4]),
                                "volume": int(float(parts[5])),
                                "amount": float(parts[6])
                            }
                            
                            # 第一条用于获取昨收，不加入返回
                            if i == 0 and len(klines_raw) > limit:
                                yesterday_close = kline_data["close"]
                            else:
                                klines.append(kline_data)
                    
                    if klines:
                        logger.info(f"✅ 东方财富获取K线数据成功: {clean_code} - {len(klines)}条")
                        return {
                            "code": clean_code,
                            "name": stock_name,
                            "period": period,
                            "klines": klines,
                            "yesterday_close": yesterday_close,
                            "data_source": "eastmoney"
                        }
                    
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"东方财富K线API超时: {stock_code}")
            return None
        except Exception as e:
            logger.warning(f"东方财富K线API异常: {stock_code} -> {e}")
            return None


class TencentDataSource(StockDataSource):
    """腾讯数据源 (备用)"""
    
    MINUTE_URL = "https://web.ifzq.gtimg.cn/appstock/app/minute/query"
    KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
    
    def _format_code(self, stock_code: str) -> str:
        """格式化股票代码"""
        clean_code = stock_code.replace("sh", "").replace("sz", "").replace("hk", "")
        
        if stock_code.startswith("sh") or clean_code.startswith("6"):
            return f"sh{clean_code}"
        elif stock_code.startswith("hk"):
            return f"hk{clean_code}"
        else:
            return f"sz{clean_code}"
    
    async def get_minute_data(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取分时数据"""
        # 清除代理环境变量
        for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
            os.environ.pop(k, None)
        
        code = self._format_code(stock_code)
        clean_code = stock_code.replace("sh", "").replace("sz", "").replace("hk", "")
        
        params = {"code": code}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        connector = aiohttp.TCPConnector(ssl=False)
        
        try:
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                async with session.get(
                    self.MINUTE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"腾讯分时API返回 {response.status}")
                        return None
                    
                    # 腾讯API可能返回text/html, 需要处理
                    data = await response.json(content_type=None)
                    
                    if data.get("code") != 0:
                        logger.warning(f"腾讯分时API返回错误: {data.get('code')}")
                        return None
                    
                    stock_data = data.get("data", {}).get(code, {})
                    if not stock_data:
                        return None
                    
                    qt_data = stock_data.get("qt", {}).get(code, [])
                    minute_raw = stock_data.get("data", {}).get("data", [])
                    
                    # 获取昨收
                    preclose = float(qt_data[4]) if len(qt_data) > 4 else 0
                    stock_name = qt_data[1] if len(qt_data) > 1 else f"股票{clean_code}"
                    
                    if not minute_raw:
                        return None
                    
                    minute_data = []
                    last_cumulative_volume = 0
                    last_cumulative_amount = 0.0
                    
                    for item in minute_raw:
                        parts = item.split(" ") if isinstance(item, str) else []
                        if len(parts) >= 3:
                            price = float(parts[1])
                            
                            # Tencent data provides CUMULATIVE volume (lots) and amount
                            current_cumulative_vol_lots = int(parts[2])
                            current_cumulative_vol = current_cumulative_vol_lots * 100 
                            
                            # Amount is also cumulative
                            current_cumulative_amount = float(parts[3]) if len(parts) > 3 else 0.0
                            
                            # Calculate incremental volume and amount for this minute
                            minute_vol = current_cumulative_vol - last_cumulative_volume
                            minute_amount = current_cumulative_amount - last_cumulative_amount
                            
                            # Handle edge case where values might decrease/reset
                            if minute_vol < 0: minute_vol = current_cumulative_vol
                            if minute_amount < 0: minute_amount = current_cumulative_amount
                                
                            # Update last cumulative
                            last_cumulative_volume = current_cumulative_vol
                            last_cumulative_amount = current_cumulative_amount
                            
                            # Calculate VWAP using cumulative values
                            # avg_price = cumulative_amount / cumulative_volume
                            avg_price = current_cumulative_amount / current_cumulative_vol if current_cumulative_vol > 0 else price
                            
                            # Format time from HHMM to HH:MM
                            time_str = parts[0]
                            if len(time_str) == 4 and ":" not in time_str:
                                time_str = f"{time_str[:2]}:{time_str[2:]}"
                            
                            minute_data.append({
                                "time": time_str,
                                "price": price,
                                "volume": minute_vol, 
                                "amount": minute_amount, 
                                "avg_price": round(avg_price, 3)
                            })
                    
                            
                    if minute_data:
                        logger.info(f"✅ 腾讯获取分时数据成功: {clean_code} - {len(minute_data)}条")
                        return {
                            "code": clean_code,
                            "name": stock_name,
                            "minute_data": minute_data,
                            "yesterday_close": preclose,
                            "data_source": "tencent"
                        }
                    
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"腾讯分时API超时: {stock_code}")
            return None
        except Exception as e:
            logger.warning(f"腾讯分时API异常: {stock_code} -> {e}")
            return None
            
    def _synthesize_kline(self, minute_data: List[Dict], period_minutes: int, limit: int) -> List[Dict]:
        """从分时数据合成K线"""
        if not minute_data or period_minutes <= 0:
            return []
            
        klines = []
        buffer = []
        current_period_start = None
        
        for item in minute_data:
            time_str = item['time']  # "09:30"
            if ":" not in time_str and len(time_str) == 4:
                time_str = f"{time_str[:2]}:{time_str[2:]}"
                
            parts = time_str.split(':')
            hour = int(parts[0])
            minute = int(parts[1])
            
            # 计算从09:30开始的分钟数
            if hour < 13:
                minutes_from_start = (hour - 9) * 60 + (minute - 30)
            else:
                minutes_from_start = 120 + (hour - 13) * 60 + minute
            
            period_index = minutes_from_start // period_minutes
            
            if current_period_start is None:
                current_period_start = period_index
            
            if period_index != current_period_start:
                if buffer:
                    end_minutes = (current_period_start + 1) * period_minutes
                    kline = self._create_kline(buffer, end_minutes)
                    if kline:
                        klines.append(kline)
                buffer = []
                current_period_start = period_index
            
            buffer.append(item)
            
        if buffer:
            end_minutes = (current_period_start + 1) * period_minutes
            kline = self._create_kline(buffer, end_minutes)
            if kline:
                klines.append(kline)
                
        return klines[-limit:] if len(klines) > limit else klines
        
    def _create_kline(self, buffer: List[Dict], end_minutes: int) -> Optional[Dict]:
        if not buffer:
            return None
            
        open_price = buffer[0]['price']
        close_price = buffer[-1]['price']
        high_price = max(item['price'] for item in buffer)
        low_price = min(item['price'] for item in buffer)
        volume = sum(item.get('volume', 0) for item in buffer)
        amount = sum(item.get('amount', 0) for item in buffer)
        
        # Calculate time string
        if end_minutes <= 120:
             hour = 9 + (end_minutes + 30) // 60
             minute = (end_minutes + 30) % 60
             if hour > 11 or (hour == 11 and minute > 30):
                 hour, minute = 11, 30
        else:
             afternoon_minutes = end_minutes - 120
             hour = 13 + afternoon_minutes // 60
             minute = afternoon_minutes % 60
             if hour > 15 or (hour == 15 and minute > 0):
                 hour, minute = 15, 0
                 
        return {
            "date": f"{hour:02d}:{minute:02d}",
            "open": open_price,
            "close": close_price,
            "high": high_price,
            "low": low_price,
            "volume": volume,
            "amount": amount
        }
    
    async def get_kline_data(self, stock_code: str, period: str = "daily", limit: int = 100) -> Optional[Dict[str, Any]]:
        """获取K线数据"""
        # 1. 尝试合成 K 线 (针对分钟级)
        minute_periods = {'5min': 5, '15min': 15, '30min': 30, '60min': 60}
        if period in minute_periods:
            try:
                # 获取分时数据用于合成
                minute_res = await self.get_minute_data(stock_code)
                if minute_res and minute_res.get('minute_data'):
                    clean_code = stock_code.replace("sh", "").replace("sz", "").replace("hk", "")
                    klines = self._synthesize_kline(minute_res['minute_data'], minute_periods[period], limit)
                    if klines:
                        logger.info(f"✅ 腾讯合成K线成功: {clean_code} {period}")
                        return {
                            "code": clean_code,
                            "name": minute_res.get('name', '未知'),
                            "period": period,
                            "klines": klines,
                            "yesterday_close": minute_res.get('yesterday_close'),
                            "data_source": "tencent_synthesized"
                        }
            except Exception as e:
                logger.warning(f"腾讯合成K线失败: {e}")

        # 清除代理
        for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
            os.environ.pop(k, None)
            
        code = self._format_code(stock_code)
        clean_code = stock_code.replace("sh", "").replace("sz", "").replace("hk", "")
        
        # 腾讯K线参数: param=sh600519,day,,,100,qfq
        # 周期映射: day, week, month, m5, m15, m30, m60
        t_period = "day"
        if period == "weekly":
            t_period = "week"
        elif period == "monthly":
            t_period = "month"
        elif period == "5min":
            t_period = "m5"
        elif period == "15min":
            t_period = "m15"
        elif period == "30min":
            t_period = "m30"
        elif period == "60min":
            t_period = "m60"
            
        params = {"param": f"{code},{t_period},,,{limit},qfq"}
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        connector = aiohttp.TCPConnector(ssl=False)
        
        try:
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                async with session.get(
                    self.KLINE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"腾讯K线API返回 {response.status}")
                        return None
                    
                    data = await response.json(content_type=None)
                    
                    if data.get("code") != 0:
                        return None
                        
                    # 解析数据结构: data.data.{code}.qfq{day} or data.data.{code}.{day}
                    stock_data = data.get("data", {}).get(code, {})
                    
                    # 尝试获取前复权数据
                    kline_key = f"qfq{t_period}"
                    klines = stock_data.get(kline_key)
                    
                    # 如果没有复权数据，尝试获取原始数据
                    if not klines:
                        klines = stock_data.get(t_period)
                        
                    if not klines:
                        return None
                        
                    # 提取股票名称
                    name = stock_data.get("qt", {}).get(code, [])[1] if stock_data.get("qt") else f"股票{clean_code}"
                    
                    result_klines = []
                    for item in klines:
                        # 格式: [date, open, close, high, low, volume, ...]
                        if len(item) >= 6:
                            result_klines.append({
                                "date": item[0],
                                "open": float(item[1]),
                                "close": float(item[2]),
                                "high": float(item[3]),
                                "low": float(item[4]),
                                "volume": float(item[5])
                            })
                            
                    # 获取昨收 (从qt获取或者计算)
                    yesterday_close = float(stock_data.get("qt", {}).get(code, [])[4]) if stock_data.get("qt") else None
                    if yesterday_close is None and len(result_klines) > 1:
                        yesterday_close = result_klines[-2]["close"]

                    if result_klines:
                         logger.info(f"✅ 腾讯获取K线数据成功: {clean_code} - {len(result_klines)}条")
                         return {
                            "code": clean_code,
                            "name": name,
                            "period": period,
                            "klines": result_klines,
                            "yesterday_close": yesterday_close,
                            "data_source": "tencent"
                        }
                    return None
                    
        except Exception as e:
            logger.warning(f"腾讯K线API异常: {stock_code} -> {e}")
            return None


class AkShareDataSource(StockDataSource):
    """AkShare数据源 (最终备用)"""
    
    def __init__(self):
        self._akshare_available: Optional[bool] = None
    
    def _check_akshare(self) -> bool:
        """检查 akshare 是否可用"""
        if self._akshare_available is None:
            try:
                import akshare  # noqa: F401
                self._akshare_available = True
            except ImportError:
                self._akshare_available = False
                logger.warning("akshare 未安装，AkShare数据源不可用")
        return self._akshare_available
    
    async def get_minute_data(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """使用 akshare 获取分时成交数据"""
        if not self._check_akshare():
            return None
        
        clean_code = stock_code.replace("sh", "").replace("sz", "").replace("hk", "")
        
        def fetch_akshare():
            # 清除代理环境变量
            for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
                os.environ.pop(k, None)
            
            import akshare as ak
            
            # 获取分时成交数据
            df = ak.stock_intraday_em(symbol=clean_code)
            if df is None or df.empty:
                return None
            
            # 转换为标准格式 - 按时间聚合
            df["时间"] = df["时间"].astype(str).str[:5]
            grouped = df.groupby("时间").agg({
                "成交价": "last",
                "手数": "sum"
            }).reset_index()
            
            minute_data = []
            first_price = None
            
            cumulative_volume = 0
            cumulative_amount = 0.0
            
            for _, row in grouped.iterrows():
                price = float(row["成交价"])
                if first_price is None:
                    first_price = price
                
                volume = int(row["手数"]) * 100
                amount = price * volume  # 估算成交额
                
                cumulative_volume += volume
                cumulative_amount += amount
                
                avg_price = cumulative_amount / cumulative_volume if cumulative_volume > 0 else price
                
                minute_data.append({
                    "time": row["时间"],
                    "price": price,
                    "volume": volume,
                    "amount": amount,
                    "avg_price": round(avg_price, 3)
                })
            
            # 昨收价用第一个价格估算
            yesterday_close = round(first_price / 1.05, 2) if first_price else 0
            
            return {
                "code": clean_code,
                "name": f"股票{clean_code}",
                "minute_data": minute_data,
                "yesterday_close": yesterday_close,
                "data_source": "akshare"
            }
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, fetch_akshare)
            if result:
                logger.info(f"✅ AkShare获取分时数据成功: {clean_code}")
            return result
        except Exception as e:
            logger.warning(f"AkShare分时数据异常: {stock_code} -> {e}")
            return None
    
    async def get_kline_data(self, stock_code: str, period: str = "daily", limit: int = 100) -> Optional[Dict[str, Any]]:
        """使用 akshare 获取K线数据"""
        if not self._check_akshare():
            return None
        
        clean_code = stock_code.replace("sh", "").replace("sz", "").replace("hk", "")
        
        def fetch_akshare():
            for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
                os.environ.pop(k, None)
            
            import akshare as ak
            
            # 根据period选择不同的akshare函数
            if period in ("daily", "day"):
                df = ak.stock_zh_a_hist(symbol=clean_code, period="daily", adjust="qfq")
            elif period == "weekly":
                df = ak.stock_zh_a_hist(symbol=clean_code, period="weekly", adjust="qfq")
            elif period == "monthly":
                df = ak.stock_zh_a_hist(symbol=clean_code, period="monthly", adjust="qfq")
            elif period in ("5min", "15min", "30min", "60min"):
                # AkShare 分钟线 period 参数: "5", "15", "30", "60"
                period_map = {
                    "5min": "5",
                    "15min": "15",
                    "30min": "30",
                    "60min": "60"
                }
                df = ak.stock_zh_a_hist_min_em(symbol=clean_code, period=period_map[period], adjust="qfq")
            else:
                return None
            
            if df is None or df.empty:
                return None
            
            # 只取最近limit条
            df = df.tail(limit)
            
            klines = []
            for _, row in df.iterrows():
                # 分钟线通常用 "时间"，日线通常用 "日期"
                date_str = str(row.get("时间", row.get("日期", "")))
                klines.append({
                    "date": date_str,
                    "open": float(row["开盘"]),
                    "close": float(row["收盘"]),
                    "high": float(row["最高"]),
                    "low": float(row["最低"]),
                    "volume": int(row["成交量"]),
                    "amount": float(row.get("成交额", 0))
                })
            
            yesterday_close = klines[0]["close"] if len(klines) > 1 else None
            
            return {
                "code": clean_code,
                "name": f"股票{clean_code}",
                "period": period,
                "klines": klines,
                "yesterday_close": yesterday_close,
                "data_source": "akshare"
            }
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, fetch_akshare)
            if result:
                logger.info(f"✅ AkShare获取K线数据成功: {clean_code}")
            return result
        except Exception as e:
            logger.warning(f"AkShare K线数据异常: {stock_code} -> {e}")
            return None


class StockDataManager:
    """
    股票数据管理器 - 统一数据获取入口
    
    实现 fallback 链:
    东方财富 -> 腾讯 -> AkShare -> 快照
    """
    
    def __init__(self):
        self.eastmoney = EastMoneyDataSource(timeout=3.0)
        self.tencent = TencentDataSource(timeout=3.0)
        self.akshare = AkShareDataSource()
        self._snapshot: Optional[Dict[str, Any]] = None
    
    def set_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """设置快照数据 (用于最终fallback)"""
        self._snapshot = snapshot
    
    async def get_minute_data(self, stock_code: str) -> Dict[str, Any]:
        """
        获取分时数据 (带 fallback)
        
        Returns:
            分时数据字典，包含 minute_data 列表
        """
        clean_code = stock_code.replace("sh", "").replace("sz", "").replace("hk", "")
        
        # 1. 东方财富 (主数据源)
        try:
            result = await asyncio.wait_for(
                self.eastmoney.get_minute_data(stock_code),
                timeout=4.0
            )
            if result and result.get("minute_data"):
                return result
        except asyncio.TimeoutError:
            logger.warning(f"东方财富分时超时: {stock_code}")
        except Exception as e:
            logger.warning(f"东方财富分时失败: {stock_code} -> {e}")
        
        # 2. 腾讯 (备用)
        try:
            result = await asyncio.wait_for(
                self.tencent.get_minute_data(stock_code),
                timeout=4.0
            )
            if result and result.get("minute_data"):
                return result
        except Exception as e:
            logger.warning(f"腾讯分时失败: {stock_code} -> {e}")
        
        # 3. AkShare (最终备用)
        try:
            result = await self.akshare.get_minute_data(stock_code)
            if result and result.get("minute_data"):
                return result
        except Exception as e:
            logger.warning(f"AkShare分时失败: {stock_code} -> {e}")
        
        # 4. 所有数据源失败，返回None (将回退到Snapshot)
        return None
    
    async def get_kline_data(self, stock_code: str, period: str = "daily", limit: int = 100) -> Dict[str, Any]:
        """
        获取K线数据 (带 fallback)
        
        Returns:
            K线数据字典，包含 klines 列表
        """
        clean_code = stock_code.replace("sh", "").replace("sz", "").replace("hk", "")
        
        # 1. 东方财富 (主数据源)
        try:
            result = await asyncio.wait_for(
                self.eastmoney.get_kline_data(stock_code, period, limit),
                timeout=5.0
            )
            if result and result.get("klines"):
                return result
        except asyncio.TimeoutError:
            logger.warning(f"东方财富K线超时: {stock_code}")
        except Exception as e:
            logger.warning(f"东方财富K线失败: {stock_code} -> {e}")
        
        # 2. 腾讯 (备用)
        try:
            result = await asyncio.wait_for(
                self.tencent.get_kline_data(stock_code, period, limit),
                timeout=4.0
            )
            if result and result.get("klines"):
                return result
        except asyncio.TimeoutError:
            logger.warning(f"腾讯K线超时: {stock_code}")
        except Exception as e:
            logger.warning(f"腾讯K线失败: {stock_code} -> {e}")
        
        # 3. AkShare (最终备用)
        try:
            result = await self.akshare.get_kline_data(stock_code, period, limit)
            if result and result.get("klines"):
                return result
        except Exception as e:
            logger.warning(f"AkShare K线失败: {stock_code} -> {e}")
        
        # 4. 所有数据源失败，返回None (回退到快照或空)
        return None
    
    async def get_realtime_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取实时行情数据 (带 fallback)
        
        从分时数据中提取最新价格等信息作为实时行情
        
        Returns:
            实时行情字典，包含 current_price, change_percent, volume 等
        """
        clean_code = stock_code.replace("sh", "").replace("sz", "").replace("hk", "")
        
        # 1. 东方财富 (主数据源) - 从分时数据获取最新价格
        try:
            result = await asyncio.wait_for(
                self.eastmoney.get_minute_data(stock_code),
                timeout=4.0
            )
            if result and result.get("minute_data"):
                # 从分时数据中提取最新一条作为实时行情
                minute_data = result["minute_data"]
                if minute_data:
                    latest = minute_data[-1]  # 最新一条
                    return {
                        "name": result.get("name", ""),
                        "current_price": float(latest.get("price", 0)),
                        "change": float(latest.get("price", 0)) - float(result.get("yesterday_close", 0)),
                        "change_percent": ((float(latest.get("price", 0)) - float(result.get("yesterday_close", 0))) / float(result.get("yesterday_close", 1))) * 100 if result.get("yesterday_close") else 0,
                        "volume": sum(m.get("volume", 0) for m in minute_data),
                        "amount": sum(m.get("price", 0) * m.get("volume", 0) for m in minute_data),
                        "high_price": max(m.get("price", 0) for m in minute_data),
                        "low_price": min(m.get("price", 0) for m in minute_data),
                        "open_price": minute_data[0].get("price", 0) if minute_data else 0,
                        "yesterday_close": result.get("yesterday_close", 0),
                        "turnover_rate": 0,  # 需要额外计算
                        "market_value": 0,  # 需要额外计算
                        "data_source": "eastmoney"
                    }
        except asyncio.TimeoutError:
            logger.warning(f"东方财富实时行情超时: {stock_code}")
        except Exception as e:
            logger.warning(f"东方财富实时行情失败: {stock_code} -> {e}")
        
        # 2. 腾讯 (备用)
        try:
            result = await asyncio.wait_for(
                self.tencent.get_minute_data(stock_code),
                timeout=4.0
            )
            if result and result.get("minute_data"):
                minute_data = result["minute_data"]
                if minute_data:
                    latest = minute_data[-1]
                    return {
                        "name": result.get("name", ""),
                        "current_price": float(latest.get("price", 0)),
                        "change": float(latest.get("price", 0)) - float(result.get("yesterday_close", 0)),
                        "change_percent": ((float(latest.get("price", 0)) - float(result.get("yesterday_close", 0))) / float(result.get("yesterday_close", 1))) * 100 if result.get("yesterday_close") else 0,
                        "volume": sum(m.get("volume", 0) for m in minute_data),
                        "amount": sum(m.get("price", 0) * m.get("volume", 0) for m in minute_data),
                        "high_price": max(m.get("price", 0) for m in minute_data),
                        "low_price": min(m.get("price", 0) for m in minute_data),
                        "open_price": minute_data[0].get("price", 0) if minute_data else 0,
                        "yesterday_close": result.get("yesterday_close", 0),
                        "turnover_rate": 0,
                        "market_value": 0,
                        "data_source": "tencent"
                    }
        except Exception as e:
            logger.warning(f"腾讯实时行情失败: {stock_code} -> {e}")
        
        # 3. AkShare (最终备用)
        try:
            result = await self.akshare.get_minute_data(stock_code)
            if result and result.get("minute_data"):
                minute_data = result["minute_data"]
                if minute_data:
                    latest = minute_data[-1]
                    return {
                        "name": result.get("name", ""),
                        "current_price": float(latest.get("price", 0)),
                        "change": float(latest.get("price", 0)) - float(result.get("yesterday_close", 0)),
                        "change_percent": ((float(latest.get("price", 0)) - float(result.get("yesterday_close", 0))) / float(result.get("yesterday_close", 1))) * 100 if result.get("yesterday_close") else 0,
                        "volume": sum(m.get("volume", 0) for m in minute_data),
                        "amount": sum(m.get("price", 0) * m.get("volume", 0) for m in minute_data),
                        "high_price": max(m.get("price", 0) for m in minute_data),
                        "low_price": min(m.get("price", 0) for m in minute_data),
                        "open_price": minute_data[0].get("price", 0) if minute_data else 0,
                        "yesterday_close": result.get("yesterday_close", 0),
                        "turnover_rate": 0,
                        "market_value": 0,
                        "data_source": "akshare"
                    }
        except Exception as e:
            logger.warning(f"AkShare实时行情失败: {stock_code} -> {e}")
        
        # 4. 所有数据源失败，返回None
        return None


# 全局数据管理器实例
_data_manager: Optional[StockDataManager] = None


def get_stock_data_manager() -> StockDataManager:
    """获取全局数据管理器实例"""
    global _data_manager
    if _data_manager is None:
        _data_manager = StockDataManager()
    return _data_manager
