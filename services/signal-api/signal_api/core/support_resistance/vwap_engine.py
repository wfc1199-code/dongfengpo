"""
VWAP Engine - 成交量加权平均价

VWAP (Volume Weighted Average Price) 是机构交易员最常用的参考价格。
- VWAP 本身是动态支撑/压力
- ±1σ 和 ±2σ 标准差带提供额外的支撑压力区间
"""
from typing import List, Optional
import statistics
from .models import SRLevel, SRType, SRRating, SRSource


class VWAPEngine:
    """
    Level 2: VWAP 成交量加权平均价系统
    """

    def calculate(self,
                  prices: List[float],
                  volumes: Optional[List[float]] = None,
                  highs: Optional[List[float]] = None,
                  lows: Optional[List[float]] = None) -> List[SRLevel]:
        """
        计算 VWAP 及其标准差带

        Args:
            prices: 收盘价序列
            volumes: 成交量序列
            highs: 最高价序列
            lows: 最低价序列

        Returns:
            List[SRLevel]: VWAP 相关的支撑压力线
        """
        if not prices or len(prices) < 5:
            return []

        # 如果没有成交量，使用均匀分布
        vols = volumes if volumes else [1.0] * len(prices)

        # 计算典型价格 (Typical Price = (H + L + C) / 3)
        if highs and lows and len(highs) == len(prices) and len(lows) == len(prices):
            typical_prices = [
                (highs[i] + lows[i] + prices[i]) / 3
                for i in range(len(prices))
            ]
        else:
            typical_prices = prices

        # 计算 VWAP
        vwap_values = self._calculate_vwap_series(typical_prices, vols)

        if not vwap_values:
            return []

        current_vwap = vwap_values[-1]
        current_price = prices[-1]

        # 计算标准差
        deviations = [
            typical_prices[i] - vwap_values[i]
            for i in range(len(typical_prices))
        ]
        std_dev = statistics.stdev(deviations) if len(deviations) > 1 else 0

        # 构建 SRLevel 列表
        levels: List[SRLevel] = []

        # VWAP 本身
        vwap_type = SRType.SUPPORT if current_vwap < current_price else SRType.RESISTANCE
        levels.append(SRLevel(
            price=round(current_vwap, 3),
            type=vwap_type,
            strength=85.0,
            rating=SRRating.S,
            source=[SRSource.DYNAMIC],
            visual_style={
                "color": "#ec4899",  # 粉色表示 VWAP
                "lineStyle": "solid",
                "lineWidth": 2.5,
                "opacity": 0.9
            },
            description="VWAP (成交量加权均价)"
        ))

        # +1σ 上轨
        upper_1 = current_vwap + std_dev
        if std_dev > 0 and abs(upper_1 - current_vwap) / current_vwap > 0.002:
            levels.append(SRLevel(
                price=round(upper_1, 3),
                type=SRType.RESISTANCE,
                strength=70.0,
                rating=SRRating.B,
                source=[SRSource.DYNAMIC],
                visual_style={
                    "color": "#f472b6",  # 浅粉色
                    "lineStyle": "dashed",
                    "lineWidth": 1.5,
                    "opacity": 0.7
                },
                description="VWAP +1σ"
            ))

        # +2σ 上轨 (极端压力)
        upper_2 = current_vwap + 2 * std_dev
        if std_dev > 0 and abs(upper_2 - upper_1) / upper_1 > 0.002:
            levels.append(SRLevel(
                price=round(upper_2, 3),
                type=SRType.RESISTANCE,
                strength=60.0,
                rating=SRRating.C,
                source=[SRSource.DYNAMIC],
                visual_style={
                    "color": "#fda4af",  # 更浅的粉色
                    "lineStyle": "dotted",
                    "lineWidth": 1,
                    "opacity": 0.5
                },
                description="VWAP +2σ (极端压力)"
            ))

        # -1σ 下轨
        lower_1 = current_vwap - std_dev
        if std_dev > 0 and abs(lower_1 - current_vwap) / current_vwap > 0.002:
            levels.append(SRLevel(
                price=round(lower_1, 3),
                type=SRType.SUPPORT,
                strength=70.0,
                rating=SRRating.B,
                source=[SRSource.DYNAMIC],
                visual_style={
                    "color": "#f472b6",
                    "lineStyle": "dashed",
                    "lineWidth": 1.5,
                    "opacity": 0.7
                },
                description="VWAP -1σ"
            ))

        # -2σ 下轨 (极端支撑)
        lower_2 = current_vwap - 2 * std_dev
        if std_dev > 0 and abs(lower_2 - lower_1) / lower_1 > 0.002:
            levels.append(SRLevel(
                price=round(lower_2, 3),
                type=SRType.SUPPORT,
                strength=60.0,
                rating=SRRating.C,
                source=[SRSource.DYNAMIC],
                visual_style={
                    "color": "#fda4af",
                    "lineStyle": "dotted",
                    "lineWidth": 1,
                    "opacity": 0.5
                },
                description="VWAP -2σ (极端支撑)"
            ))

        return levels

    def _calculate_vwap_series(self,
                               typical_prices: List[float],
                               volumes: List[float]) -> List[float]:
        """
        计算 VWAP 序列

        VWAP = Σ(Typical Price × Volume) / Σ(Volume)
        """
        if not typical_prices or not volumes:
            return []

        vwap_values = []
        cumulative_pv = 0.0
        cumulative_volume = 0.0

        for i in range(len(typical_prices)):
            vol = volumes[i] if i < len(volumes) else 1.0
            cumulative_pv += typical_prices[i] * vol
            cumulative_volume += vol

            if cumulative_volume > 0:
                vwap_values.append(cumulative_pv / cumulative_volume)
            else:
                vwap_values.append(typical_prices[i])

        return vwap_values

    def get_vwap_analysis(self, current_price: float, vwap: float, std_dev: float) -> dict:
        """
        获取 VWAP 位置分析

        Returns:
            分析结果字典
        """
        if std_dev == 0:
            return {"position": "unknown", "sigma": 0}

        sigma = (current_price - vwap) / std_dev

        if sigma > 2:
            position = "极度超买 (>+2σ)"
        elif sigma > 1:
            position = "超买 (+1σ ~ +2σ)"
        elif sigma > 0:
            position = "VWAP 上方"
        elif sigma > -1:
            position = "VWAP 下方"
        elif sigma > -2:
            position = "超卖 (-1σ ~ -2σ)"
        else:
            position = "极度超卖 (<-2σ)"

        return {
            "position": position,
            "sigma": round(sigma, 2)
        }
