"""
Volume Profile Engine - 成交量分布分析

核心指标：
- POC (Point of Control): 成交量最集中的价格，是"公允价格"
- VAH/VAL (Value Area High/Low): 成交量 70% 区间的上下沿
- HVN (High Volume Node): 成交量密集节点，强支撑/压力区
- LVN (Low Volume Node): 成交量稀疏节点，快速突破区
"""
from typing import List, Optional, Dict, Tuple
from collections import defaultdict
import statistics
from .models import SRLevel, SRType, SRRating, SRSource


class VolumeProfileEngine:
    """
    Level 2: Volume Profile 成交量分布分析
    基于价格区间统计成交量，识别关键支撑压力位
    """

    def __init__(self, num_bins: int = 50, value_area_pct: float = 0.70):
        """
        Args:
            num_bins: 价格区间划分数量
            value_area_pct: Value Area 占总成交量的百分比 (默认 70%)
        """
        self.num_bins = num_bins
        self.value_area_pct = value_area_pct

    def calculate(self,
                  prices: List[float],
                  volumes: Optional[List[float]] = None,
                  highs: Optional[List[float]] = None,
                  lows: Optional[List[float]] = None) -> List[SRLevel]:
        """
        计算 Volume Profile 支撑压力线

        Args:
            prices: 收盘价序列
            volumes: 成交量序列 (如果没有则假设均匀分布)
            highs: 最高价序列 (用于更精确的分布计算)
            lows: 最低价序列

        Returns:
            List[SRLevel]: 支撑压力线列表
        """
        if not prices or len(prices) < 5:
            return []

        # 如果没有成交量数据，使用均匀分布
        if not volumes:
            volumes = [1.0] * len(prices)

        # 计算价格范围
        all_prices = prices.copy()
        if highs:
            all_prices.extend(highs)
        if lows:
            all_prices.extend(lows)

        price_min = min(all_prices)
        price_max = max(all_prices)

        if price_max <= price_min:
            return []

        # 构建成交量分布
        profile = self._build_profile(prices, volumes, highs, lows, price_min, price_max)

        if not profile:
            return []

        # 计算核心指标
        poc_price = self._calculate_poc(profile, price_min)
        val_price, vah_price = self._calculate_value_area(profile, price_min)
        hvn_levels = self._find_hvn(profile, price_min)
        lvn_levels = self._find_lvn(profile, price_min)

        # 构建 SRLevel 列表
        levels: List[SRLevel] = []
        current_price = prices[-1]

        # POC - 最强的支撑/压力位
        if poc_price:
            poc_type = SRType.SUPPORT if poc_price < current_price else SRType.RESISTANCE
            levels.append(SRLevel(
                price=round(poc_price, 3),
                type=poc_type,
                strength=90.0,
                rating=SRRating.S,
                source=[SRSource.DYNAMIC],
                visual_style={
                    "color": "#8b5cf6",  # 紫色表示 POC
                    "lineStyle": "solid",
                    "lineWidth": 3,
                    "opacity": 0.9
                },
                description="POC (成交量控制点)"
            ))

        # VAH - Value Area High
        if vah_price and abs(vah_price - poc_price) / poc_price > 0.003:
            levels.append(SRLevel(
                price=round(vah_price, 3),
                type=SRType.RESISTANCE,
                strength=75.0,
                rating=SRRating.A,
                source=[SRSource.DYNAMIC],
                visual_style={
                    "color": "#f59e0b",  # 橙色
                    "lineStyle": "dashed",
                    "lineWidth": 2,
                    "opacity": 0.8
                },
                description="VAH (价值区上沿)"
            ))

        # VAL - Value Area Low
        if val_price and abs(val_price - poc_price) / poc_price > 0.003:
            levels.append(SRLevel(
                price=round(val_price, 3),
                type=SRType.SUPPORT,
                strength=75.0,
                rating=SRRating.A,
                source=[SRSource.DYNAMIC],
                visual_style={
                    "color": "#f59e0b",  # 橙色
                    "lineStyle": "dashed",
                    "lineWidth": 2,
                    "opacity": 0.8
                },
                description="VAL (价值区下沿)"
            ))

        # HVN - High Volume Nodes (最多取3个)
        for i, hvn in enumerate(hvn_levels[:3]):
            hvn_type = SRType.SUPPORT if hvn['price'] < current_price else SRType.RESISTANCE
            levels.append(SRLevel(
                price=round(hvn['price'], 3),
                type=hvn_type,
                strength=65.0 + hvn['volume_ratio'] * 10,
                rating=SRRating.A if hvn['volume_ratio'] > 1.5 else SRRating.B,
                source=[SRSource.DYNAMIC],
                visual_style={
                    "color": "#3b82f6",  # 蓝色
                    "lineStyle": "solid",
                    "lineWidth": 1.5,
                    "opacity": 0.7
                },
                description=f"HVN (成交密集区 {hvn['volume_ratio']:.1f}x)"
            ))

        return levels

    def _build_profile(self,
                       prices: List[float],
                       volumes: List[float],
                       highs: Optional[List[float]],
                       lows: Optional[List[float]],
                       price_min: float,
                       price_max: float) -> Dict[int, float]:
        """
        构建成交量分布直方图
        """
        bin_size = (price_max - price_min) / self.num_bins
        if bin_size <= 0:
            return {}

        profile: Dict[int, float] = defaultdict(float)

        for i in range(len(prices)):
            volume = volumes[i] if i < len(volumes) else 1.0

            # 如果有高低价，在整个K线范围内分配成交量
            if highs and lows and i < len(highs) and i < len(lows):
                low = lows[i]
                high = highs[i]
                bar_range = high - low
                if bar_range > 0:
                    # 将成交量均匀分配到K线覆盖的所有bins
                    low_bin = int((low - price_min) / bin_size)
                    high_bin = int((high - price_min) / bin_size)
                    bins_covered = max(1, high_bin - low_bin + 1)
                    vol_per_bin = volume / bins_covered
                    for b in range(low_bin, high_bin + 1):
                        if 0 <= b < self.num_bins:
                            profile[b] += vol_per_bin
                else:
                    # 单价K线
                    bin_idx = int((prices[i] - price_min) / bin_size)
                    if 0 <= bin_idx < self.num_bins:
                        profile[bin_idx] += volume
            else:
                # 只有收盘价，直接分配
                bin_idx = int((prices[i] - price_min) / bin_size)
                if 0 <= bin_idx < self.num_bins:
                    profile[bin_idx] += volume

        self._bin_size = bin_size
        self._price_min = price_min
        return dict(profile)

    def _calculate_poc(self, profile: Dict[int, float], price_min: float) -> Optional[float]:
        """
        计算 POC (Point of Control) - 成交量最高的价格
        """
        if not profile:
            return None

        poc_bin = max(profile, key=profile.get)
        poc_price = price_min + (poc_bin + 0.5) * self._bin_size
        return poc_price

    def _calculate_value_area(self, profile: Dict[int, float], price_min: float) -> Tuple[Optional[float], Optional[float]]:
        """
        计算 Value Area (成交量 70% 区间)
        使用从 POC 向两侧扩展的方法
        """
        if not profile:
            return None, None

        total_volume = sum(profile.values())
        target_volume = total_volume * self.value_area_pct

        poc_bin = max(profile, key=profile.get)
        included_bins = {poc_bin}
        current_volume = profile[poc_bin]

        all_bins = sorted(profile.keys())
        min_bin = min(all_bins)
        max_bin = max(all_bins)

        while current_volume < target_volume:
            # 找到相邻但未包含的 bins
            candidates = []

            # 向下扩展
            lower_bound = min(included_bins)
            if lower_bound - 1 >= min_bin and lower_bound - 1 not in included_bins:
                candidates.append((lower_bound - 1, profile.get(lower_bound - 1, 0)))

            # 向上扩展
            upper_bound = max(included_bins)
            if upper_bound + 1 <= max_bin and upper_bound + 1 not in included_bins:
                candidates.append((upper_bound + 1, profile.get(upper_bound + 1, 0)))

            if not candidates:
                break

            # 选择成交量更大的方向
            best_bin = max(candidates, key=lambda x: x[1])[0]
            included_bins.add(best_bin)
            current_volume += profile.get(best_bin, 0)

        val_price = price_min + (min(included_bins) + 0.5) * self._bin_size
        vah_price = price_min + (max(included_bins) + 0.5) * self._bin_size

        return val_price, vah_price

    def _find_hvn(self, profile: Dict[int, float], price_min: float) -> List[Dict]:
        """
        找出 High Volume Nodes (成交量密集节点)
        超过平均成交量 1.5 倍的价格区间
        """
        if not profile:
            return []

        avg_volume = sum(profile.values()) / len(profile)
        hvn_threshold = avg_volume * 1.5

        hvn_levels = []
        for bin_idx, volume in profile.items():
            if volume >= hvn_threshold:
                hvn_levels.append({
                    'price': price_min + (bin_idx + 0.5) * self._bin_size,
                    'volume': volume,
                    'volume_ratio': volume / avg_volume
                })

        # 按成交量排序
        hvn_levels.sort(key=lambda x: x['volume'], reverse=True)
        return hvn_levels

    def _find_lvn(self, profile: Dict[int, float], price_min: float) -> List[Dict]:
        """
        找出 Low Volume Nodes (成交量稀疏节点)
        低于平均成交量 0.5 倍的价格区间
        """
        if not profile:
            return []

        avg_volume = sum(profile.values()) / len(profile)
        lvn_threshold = avg_volume * 0.5

        lvn_levels = []
        for bin_idx, volume in profile.items():
            if 0 < volume < lvn_threshold:
                lvn_levels.append({
                    'price': price_min + (bin_idx + 0.5) * self._bin_size,
                    'volume': volume,
                    'volume_ratio': volume / avg_volume
                })

        # 按成交量排序（升序，最稀疏的在前）
        lvn_levels.sort(key=lambda x: x['volume'])
        return lvn_levels
