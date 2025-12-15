from typing import List, Optional
from .models import SRLevel, SRType, SRRating, SRSource

class BasicRulesEngine:
    """
    Level 1: 简单本地规则
    包括：昨收、今开、重要整数关口
    """

    def calculate(self,
                 current_price: float,
                 prev_close: Optional[float] = None,
                 today_open: Optional[float] = None,
                 today_high: Optional[float] = None,
                 today_low: Optional[float] = None) -> List[SRLevel]:
        levels = []

        # 1. Previous Close (昨收) - 通常作为强支撑/压力
        if prev_close:
            levels.append(SRLevel(
                price=prev_close,
                type=SRType.PIVOT,
                strength=80.0,
                rating=SRRating.A,
                source=[SRSource.FIXED],
                visual_style={"color": "#9ca3af", "lineStyle": "dashed", "opacity": 0.7},
                description="昨收"
            ))

        # 2. Today Open (今开)
        if today_open:
            levels.append(SRLevel(
                price=today_open,
                type=SRType.PIVOT,
                strength=70.0,
                rating=SRRating.B,
                source=[SRSource.FIXED],
                visual_style={"color": "#fbbf24", "lineStyle": "dotted", "opacity": 0.8},
                description="今开"
            ))

        # 3. Today High/Low (日内高低)
        if today_high and today_high != today_open: # 避免重合
             levels.append(SRLevel(
                price=today_high,
                type=SRType.RESISTANCE,
                strength=75.0,
                rating=SRRating.B,
                source=[SRSource.FIXED],
                visual_style={"color": "#ef4444", "lineStyle": "solid", "opacity": 0.5},
                description="日内高点"
            ))

        if today_low and today_low != today_open:
             levels.append(SRLevel(
                price=today_low,
                type=SRType.SUPPORT,
                strength=75.0,
                rating=SRRating.B,
                source=[SRSource.FIXED],
                visual_style={"color": "#10b981", "lineStyle": "solid", "opacity": 0.5},
                description="日内低点"
            ))

        return levels

    def _get_integer_levels(self, price: float) -> List[SRLevel]:
        # Implement logic for round numbers (10, 20, 50, 100 etc)
        # Placeholder for now
        return []
