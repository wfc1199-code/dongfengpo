"""
异动检测器 - 全市场扫描

职责:
- 获取全市场/监控池股票实时行情
- 检测价格/量能/换手异动
- 输出候选股票列表供策略评估

异动条件:
- 涨幅 ≥ 5% (接近涨停区域)
- 量比 ≥ 3 (成交量放大)  
- 换手率 ≥ 3% (活跃交易)
- 涨速 ≥ 1.5%/分钟 (快速拉升)
"""

import asyncio
import logging
from datetime import datetime, time
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

import akshare as ak
import pandas as pd

logger = logging.getLogger(__name__)


class AnomalyType(Enum):
    """异动类型"""
    PRICE_SURGE = "price_surge"      # 涨幅异动
    VOLUME_SPIKE = "volume_spike"    # 量比异动
    TURNOVER_HIGH = "turnover_high"  # 换手异动
    SPEED_FAST = "speed_fast"        # 涨速异动
    COMBO = "combo"                  # 多重异动


@dataclass
class AnomalyCandidate:
    """异动候选股票"""
    code: str
    name: str
    price: float
    change_pct: float          # 涨跌幅
    volume_ratio: float        # 量比
    turnover_rate: float       # 换手率
    amount: float              # 成交额
    speed_1m: float = 0.0      # 1分钟涨速
    speed_3m: float = 0.0      # 3分钟涨速
    anomaly_types: List[AnomalyType] = field(default_factory=list)
    anomaly_score: float = 0.0  # 异动综合评分
    detected_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "code": self.code,
            "name": self.name,
            "price": self.price,
            "changePct": self.change_pct,
            "volumeRatio": self.volume_ratio,
            "turnoverRate": self.turnover_rate,
            "amount": self.amount,
            "speed1m": self.speed_1m,
            "speed3m": self.speed_3m,
            "anomalyTypes": [t.value for t in self.anomaly_types],
            "anomalyScore": self.anomaly_score,
            "detectedAt": self.detected_at.isoformat(),
        }


@dataclass
class ScannerConfig:
    """扫描配置"""
    # 异动阈值
    min_change_pct: float = 5.0       # 最低涨幅%
    min_volume_ratio: float = 3.0     # 最低量比
    min_turnover_rate: float = 3.0    # 最低换手率%
    min_speed_1m: float = 1.5         # 最低1分钟涨速%
    min_amount: float = 1e8           # 最低成交额(1亿)
    
    # 排除条件
    exclude_st: bool = True           # 排除ST
    exclude_new_stock_days: int = 60  # 排除新股(天)
    max_change_pct: float = 9.9       # 最高涨幅(排除已涨停)
    
    # 扫描范围
    watch_list: Optional[List[str]] = None  # 自选监控池
    scan_interval: int = 3            # 扫描间隔(秒)


class AnomalyScanner:
    """
    异动检测器
    
    核心功能:
    - scan(): 扫描全市场，返回异动候选列表
    - is_trading_time(): 判断是否交易时间
    """
    
    def __init__(self, config: Optional[ScannerConfig] = None):
        self.config = config or ScannerConfig()
        self._price_history: Dict[str, List[float]] = {}  # 历史价格(计算涨速)
        self._last_scan_time: Optional[datetime] = None
        self._detected_codes: Set[str] = set()  # 已检测过的代码(避免重复推送)
        
    async def scan(self) -> List[AnomalyCandidate]:
        """
        执行全市场扫描
        
        Returns:
            List[AnomalyCandidate]: 异动候选列表
        """
        if not self.is_trading_time():
            logger.debug("非交易时间，跳过扫描")
            return []
        
        try:
            # 1. 获取全市场实时行情
            df = await self._fetch_realtime_quotes()
            if df is None or df.empty:
                return []
            
            # 2. 预过滤
            df = self._prefilter(df)
            
            # 3. 检测异动
            candidates = []
            for _, row in df.iterrows():
                candidate = self._detect_anomaly(row)
                if candidate and candidate.anomaly_types:
                    candidates.append(candidate)
            
            # 4. 排序(按异动评分)
            candidates.sort(key=lambda x: x.anomaly_score, reverse=True)
            
            # 5. 更新历史
            self._update_price_history(df)
            self._last_scan_time = datetime.now()
            
            logger.info(f"扫描完成: 全市场 {len(df)} 只 → 异动 {len(candidates)} 只")
            return candidates[:50]  # 返回Top 50
            
        except Exception as e:
            logger.error(f"扫描失败: {e}")
            return []
    
    async def _fetch_realtime_quotes(self) -> Optional[pd.DataFrame]:
        """获取实时行情"""
        try:
            loop = asyncio.get_event_loop()
            
            # 使用AkShare获取全市场实时行情
            df = await loop.run_in_executor(
                None,
                ak.stock_zh_a_spot_em
            )
            
            if df is None or df.empty:
                return None
            
            # 标准化列名
            df = df.rename(columns={
                '代码': 'code',
                '名称': 'name',
                '最新价': 'price',
                '涨跌幅': 'change_pct',
                '量比': 'volume_ratio',
                '换手率': 'turnover_rate',
                '成交额': 'amount',
            })
            
            return df
            
        except Exception as e:
            logger.warning(f"获取实时行情失败: {e}")
            return None
    
    def _prefilter(self, df: pd.DataFrame) -> pd.DataFrame:
        """预过滤"""
        # 转换数值类型
        for col in ['price', 'change_pct', 'volume_ratio', 'turnover_rate', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 基本过滤
        mask = (
            (df['price'] > 0) &
            (df['change_pct'] >= self.config.min_change_pct) &
            (df['change_pct'] <= self.config.max_change_pct) &  # 排除已涨停
            (df['amount'] >= self.config.min_amount)
        )
        
        # 排除ST
        if self.config.exclude_st:
            mask &= ~df['name'].str.contains('ST', case=False, na=False)
        
        # 如果有监控池，只扫描监控池
        if self.config.watch_list:
            mask &= df['code'].isin(self.config.watch_list)
        
        return df[mask].copy()
    
    def _detect_anomaly(self, row: pd.Series) -> Optional[AnomalyCandidate]:
        """检测单只股票异动"""
        code = str(row.get('code', ''))
        name = str(row.get('name', ''))
        price = float(row.get('price', 0))
        change_pct = float(row.get('change_pct', 0))
        volume_ratio = float(row.get('volume_ratio', 0))
        turnover_rate = float(row.get('turnover_rate', 0))
        amount = float(row.get('amount', 0))
        
        anomaly_types = []
        score = 0.0
        
        # 检测涨幅异动
        if change_pct >= self.config.min_change_pct:
            anomaly_types.append(AnomalyType.PRICE_SURGE)
            score += min(change_pct / 10, 1) * 30  # 涨幅权重30
        
        # 检测量比异动
        if volume_ratio >= self.config.min_volume_ratio:
            anomaly_types.append(AnomalyType.VOLUME_SPIKE)
            score += min(volume_ratio / 10, 1) * 25  # 量比权重25
        
        # 检测换手异动
        if turnover_rate >= self.config.min_turnover_rate:
            anomaly_types.append(AnomalyType.TURNOVER_HIGH)
            score += min(turnover_rate / 20, 1) * 20  # 换手权重20
        
        # 计算涨速
        speed_1m, speed_3m = self._calculate_speed(code, price)
        if speed_1m >= self.config.min_speed_1m:
            anomaly_types.append(AnomalyType.SPEED_FAST)
            score += min(speed_1m / 3, 1) * 25  # 涨速权重25
        
        # 多重异动加成
        if len(anomaly_types) >= 3:
            anomaly_types.append(AnomalyType.COMBO)
            score *= 1.2  # 20%加成
        
        # 至少满足一个异动条件
        if not anomaly_types:
            return None
        
        return AnomalyCandidate(
            code=code,
            name=name,
            price=price,
            change_pct=change_pct,
            volume_ratio=volume_ratio,
            turnover_rate=turnover_rate,
            amount=amount,
            speed_1m=speed_1m,
            speed_3m=speed_3m,
            anomaly_types=anomaly_types,
            anomaly_score=min(score, 100),
        )
    
    def _calculate_speed(self, code: str, current_price: float) -> tuple:
        """计算涨速"""
        history = self._price_history.get(code, [])
        
        speed_1m = 0.0
        speed_3m = 0.0
        
        if history and current_price > 0:
            # 1分钟涨速 (假设3秒扫描一次，20个点约1分钟)
            if len(history) >= 1:
                prev_price = history[-1]
                if prev_price > 0:
                    speed_1m = (current_price - prev_price) / prev_price * 100
            
            # 3分钟涨速 (60个点约3分钟)
            if len(history) >= 3:
                prev_price = history[-3]
                if prev_price > 0:
                    speed_3m = (current_price - prev_price) / prev_price * 100
        
        return speed_1m, speed_3m
    
    def _update_price_history(self, df: pd.DataFrame):
        """更新价格历史"""
        for _, row in df.iterrows():
            code = str(row.get('code', ''))
            price = float(row.get('price', 0))
            
            if code and price > 0:
                if code not in self._price_history:
                    self._price_history[code] = []
                
                self._price_history[code].append(price)
                
                # 只保留最近60个点(约3分钟)
                if len(self._price_history[code]) > 60:
                    self._price_history[code] = self._price_history[code][-60:]
    
    def is_trading_time(self) -> bool:
        """判断是否交易时间"""
        now = datetime.now()
        current_time = now.time()
        
        # 周末不交易
        if now.weekday() >= 5:
            return False
        
        # 交易时段: 9:30-11:30, 13:00-15:00
        morning_start = time(9, 30)
        morning_end = time(11, 30)
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)
        
        return (
            (morning_start <= current_time <= morning_end) or
            (afternoon_start <= current_time <= afternoon_end)
        )
    
    def clear_detected(self):
        """清空已检测记录(新交易日调用)"""
        self._detected_codes.clear()
        self._price_history.clear()


# 全局单例
_scanner: Optional[AnomalyScanner] = None


def get_scanner(config: Optional[ScannerConfig] = None) -> AnomalyScanner:
    """获取扫描器单例"""
    global _scanner
    if _scanner is None:
        _scanner = AnomalyScanner(config)
    return _scanner
