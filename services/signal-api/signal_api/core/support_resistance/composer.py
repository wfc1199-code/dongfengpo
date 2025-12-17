from typing import List, Optional
import os
from .models import SRLevel, SRAnalysis, SRRequestPayload, SRResponse
from .basic_rules import BasicRulesEngine
from .tdx_engine import TDXEngine

class SRComposer:
    def __init__(self):
        self.basic_engine = BasicRulesEngine()
        self.tdx_engine = TDXEngine()

        # Feature Flag
        self.enable_tdx = os.getenv("ENABLE_TDX_SR", "true").lower() == "true"

    def calculate(self, payload: SRRequestPayload) -> SRResponse:
        all_levels: List[SRLevel] = []

        # 1. Get current price
        current_price = payload.prices[-1] if payload.prices else 0

        # 2. Run Basic Rules
        basic_levels = self.basic_engine.calculate(
            current_price=current_price,
            prev_close=payload.prev_close,
            today_open=payload.today_open,
            today_high=payload.today_high,
            today_low=payload.today_low
        )
        all_levels.extend(basic_levels)

        # 3. Run TDX Engine (if enabled)
        if self.enable_tdx:
            tdx_levels = self.tdx_engine.calculate(
                prices=payload.prices,
                highs=payload.highs,
                lows=payload.lows,
                timestamps=payload.timestamps
            )
            all_levels.extend(tdx_levels)

        # 4. Merge & Deduplicate (Simple implementation)
        # TODO: Implement sophisticated clustering/merging
        unique_levels = self._deduplicate(all_levels)

        # 5. Sort by price
        unique_levels.sort(key=lambda x: x.price, reverse=True)

        # 6. Generate Analysis
        analysis = self._generate_analysis(current_price, unique_levels)

        return SRResponse(
            success=True,
            levels=unique_levels,
            analysis=analysis
        )

    def _deduplicate(self, levels: List[SRLevel], tolerance: float = 0.005) -> List[SRLevel]:
        """
        简单的去重逻辑：如果两个线价格非常接近，保留 strength 更高的那个，或者合并 source。
        """
        if not levels:
            return []

        # Sort by price first
        sorted_levels = sorted(levels, key=lambda x: x.price)
        merged = []

        if not sorted_levels:
            return []

        current = sorted_levels[0]

        for next_level in sorted_levels[1:]:
            # Check if close enough (relative difference)
            diff_ratio = abs(next_level.price - current.price) / (current.price if current.price > 0 else 1)

            if diff_ratio < tolerance:
                # Merge
                # Take max strength
                if next_level.strength > current.strength:
                    current.strength = next_level.strength
                    current.rating = next_level.rating
                    current.type = next_level.type # Override type if stronger

                # Merge sources
                for s in next_level.source:
                    if s not in current.source:
                        current.source.append(s)

                # Merge descriptions
                if next_level.description:
                    current.description = f"{current.description} & {next_level.description}"
            else:
                merged.append(current)
                current = next_level

        merged.append(current)
        return merged

    def _generate_analysis(self, current_price: float, levels: List[SRLevel]) -> SRAnalysis:
        if not levels:
            return SRAnalysis(
                summary="No significant support or resistance levels detected.",
                dominant_trend="Neutral",
                price_position="Unknown"
            )

        # Find closest support and resistance
        supports = [l for l in levels if l.price < current_price]
        resistances = [l for l in levels if l.price > current_price]

        closest_support = max([l.price for l in supports]) if supports else None
        closest_resistance = min([l.price for l in resistances]) if resistances else None

        position_desc = "Testing levels"
        if closest_support and closest_resistance:
            position_desc = f"In Channel ({closest_support} - {closest_resistance})"
        elif closest_support:
            position_desc = "Above Support"
        elif closest_resistance:
            position_desc = "Below Resistance"

        summary = f"Detected {len(levels)} levels. "
        if closest_support:
            summary += f"Support at {closest_support}. "
        if closest_resistance:
            summary += f"Resistance at {closest_resistance}."

        return SRAnalysis(
            summary=summary,
            dominant_trend="Neutral", # Need more logic for trend
            closest_support=closest_support,
            closest_resistance=closest_resistance,
            price_position=position_desc
        )
