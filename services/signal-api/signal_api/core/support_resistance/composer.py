"""
Support/Resistance Composer - 多引擎融合与 Confluence 评分

核心设计：
1. 整合所有引擎：Basic Rules + TDX + Volume Profile + VWAP
2. Confluence 评分：多信号重叠自动加权
3. 智能去重：相近价格合并并提升评分
"""
from typing import List, Optional, Dict, Set
import os
from .models import SRLevel, SRAnalysis, SRRequestPayload, SRResponse, SRType, SRRating, SRSource
from .basic_rules import BasicRulesEngine
from .tdx_engine import TDXEngine
from .volume_profile import VolumeProfileEngine
from .vwap_engine import VWAPEngine


class SRComposer:
    """
    支撑压力融合器
    整合多个引擎的输出，实现 Confluence 评分
    """

    def __init__(self):
        self.basic_engine = BasicRulesEngine()
        self.tdx_engine = TDXEngine()
        self.volume_profile_engine = VolumeProfileEngine()
        self.vwap_engine = VWAPEngine()

        # Feature Flags
        self.enable_tdx = os.getenv("ENABLE_TDX_SR", "true").lower() == "true"
        self.enable_volume_profile = os.getenv("ENABLE_VOLUME_PROFILE_SR", "true").lower() == "true"
        self.enable_vwap = os.getenv("ENABLE_VWAP_SR", "true").lower() == "true"

        # Confluence 配置
        self.confluence_tolerance = 0.005  # 0.5% 价差视为重叠
        self.max_levels_output = 12  # 最多输出的线条数量

    def calculate(self, payload: SRRequestPayload) -> SRResponse:
        """
        主计算入口：融合所有引擎并进行 Confluence 评分
        """
        all_levels: List[SRLevel] = []

        # 1. 获取当前价格
        current_price = payload.prices[-1] if payload.prices else 0

        # 2. 运行 Basic Rules (始终启用)
        basic_levels = self.basic_engine.calculate(
            current_price=current_price,
            prev_close=payload.prev_close,
            today_open=payload.today_open,
            today_high=payload.today_high,
            today_low=payload.today_low
        )
        all_levels.extend(basic_levels)

        # 3. 运行 TDX Engine
        if self.enable_tdx and payload.prices:
            tdx_levels = self.tdx_engine.calculate(
                prices=payload.prices,
                highs=payload.highs,
                lows=payload.lows,
                volumes=payload.volumes,
                timestamps=payload.timestamps
            )
            all_levels.extend(tdx_levels)

        # 4. 运行 Volume Profile
        if self.enable_volume_profile and payload.prices and payload.volumes:
            vp_levels = self.volume_profile_engine.calculate(
                prices=payload.prices,
                volumes=payload.volumes,
                highs=payload.highs,
                lows=payload.lows
            )
            all_levels.extend(vp_levels)

        # 5. 运行 VWAP
        if self.enable_vwap and payload.prices:
            vwap_levels = self.vwap_engine.calculate(
                prices=payload.prices,
                volumes=payload.volumes,
                highs=payload.highs,
                lows=payload.lows
            )
            all_levels.extend(vwap_levels)

        # 6. Confluence 融合评分
        confluenced_levels = self._apply_confluence(all_levels, current_price)

        # 7. 按强度排序并裁剪
        confluenced_levels.sort(key=lambda x: x.strength, reverse=True)
        top_levels = confluenced_levels[:self.max_levels_output]

        # 8. 按价格重新排序 (方便展示)
        top_levels.sort(key=lambda x: x.price, reverse=True)

        # 9. 生成分析
        analysis = self._generate_analysis(current_price, top_levels)

        return SRResponse(
            success=True,
            levels=top_levels,
            analysis=analysis,
            metadata={
                "total_raw_levels": len(all_levels),
                "after_confluence": len(confluenced_levels),
                "engines_enabled": {
                    "basic_rules": True,
                    "tdx": self.enable_tdx,
                    "volume_profile": self.enable_volume_profile,
                    "vwap": self.enable_vwap
                }
            }
        )

    def _apply_confluence(self, levels: List[SRLevel], current_price: float) -> List[SRLevel]:
        """
        Confluence 融合评分算法

        核心逻辑：
        1. 按价格聚类相近的线
        2. 多信号重叠时提升强度评分
        3. 合并来源标签
        """
        if not levels:
            return []

        # 按价格排序
        sorted_levels = sorted(levels, key=lambda x: x.price)

        # 聚类合并
        clusters: List[Dict] = []
        current_cluster: Dict = {
            'levels': [sorted_levels[0]],
            'price_sum': sorted_levels[0].price,
            'sources': set(sorted_levels[0].source),
            'descriptions': [sorted_levels[0].description] if sorted_levels[0].description else [],
            'max_strength': sorted_levels[0].strength,
            'types': [sorted_levels[0].type]
        }

        for level in sorted_levels[1:]:
            avg_price = current_cluster['price_sum'] / len(current_cluster['levels'])
            diff_ratio = abs(level.price - avg_price) / avg_price if avg_price > 0 else 1

            if diff_ratio <= self.confluence_tolerance:
                # 加入当前聚类
                current_cluster['levels'].append(level)
                current_cluster['price_sum'] += level.price
                current_cluster['sources'].update(level.source)
                if level.description:
                    current_cluster['descriptions'].append(level.description)
                current_cluster['max_strength'] = max(current_cluster['max_strength'], level.strength)
                current_cluster['types'].append(level.type)
            else:
                # 完成当前聚类，开始新聚类
                clusters.append(self._finalize_cluster(current_cluster, current_price))
                current_cluster = {
                    'levels': [level],
                    'price_sum': level.price,
                    'sources': set(level.source),
                    'descriptions': [level.description] if level.description else [],
                    'max_strength': level.strength,
                    'types': [level.type]
                }

        # 添加最后一个聚类
        clusters.append(self._finalize_cluster(current_cluster, current_price))

        return clusters

    def _finalize_cluster(self, cluster: Dict, current_price: float) -> SRLevel:
        """
        完成聚类：计算 Confluence 加成并生成最终 SRLevel
        """
        num_sources = len(cluster['sources'])
        base_strength = cluster['max_strength']

        # Confluence 加成
        # 2个来源: +15%
        # 3个来源: +30%
        # 4个来源以上: +50%
        if num_sources >= 4:
            confluence_bonus = 0.50
        elif num_sources >= 3:
            confluence_bonus = 0.30
        elif num_sources >= 2:
            confluence_bonus = 0.15
        else:
            confluence_bonus = 0

        final_strength = min(base_strength * (1 + confluence_bonus), 100)

        # 重新计算评级
        rating = self._strength_to_rating(final_strength)

        # 计算平均价格
        avg_price = cluster['price_sum'] / len(cluster['levels'])

        # 决定类型
        type_counts = {}
        for t in cluster['types']:
            type_counts[t] = type_counts.get(t, 0) + 1
        dominant_type = max(type_counts, key=type_counts.get)

        # 如果类型不明确，根据相对位置决定
        # 注意：由于 Pydantic use_enum_values=True，类型可能是字符串
        pivot_val = SRType.PIVOT.value if hasattr(SRType.PIVOT, 'value') else 'pivot'
        if dominant_type == pivot_val or dominant_type == SRType.PIVOT:
            dominant_type = SRType.SUPPORT if avg_price < current_price else SRType.RESISTANCE

        # 构建描述
        sources_str = " + ".join(sorted([s.value if hasattr(s, 'value') else str(s) for s in cluster['sources']]))
        if num_sources > 1:
            description = f"★ Confluence ({num_sources}源): {sources_str}"
        else:
            description = cluster['descriptions'][0] if cluster['descriptions'] else sources_str

        # 视觉样式
        visual_style = self._get_confluence_visual_style(final_strength, dominant_type, num_sources)

        return SRLevel(
            price=round(avg_price, 3),
            type=dominant_type,
            strength=round(final_strength, 1),
            rating=rating,
            source=list(cluster['sources']),
            visual_style=visual_style,
            description=description
        )

    def _strength_to_rating(self, strength: float) -> SRRating:
        """强度转评级"""
        if strength >= 85:
            return SRRating.S
        elif strength >= 70:
            return SRRating.A
        elif strength >= 55:
            return SRRating.B
        else:
            return SRRating.C

    def _get_confluence_visual_style(self, strength: float, sr_type: SRType, num_sources: int) -> dict:
        """
        根据 Confluence 强度生成视觉样式
        """
        # 基础颜色
        # 注意: sr_type 可能是 SRType 枚举或字符串值
        is_resistance = (sr_type == SRType.RESISTANCE or 
                         sr_type == SRType.RESISTANCE.value or 
                         str(sr_type) == 'resistance')
        
        if num_sources >= 3:
            # 高 Confluence = 金色
            color = "#fbbf24" if is_resistance else "#22c55e"
        elif is_resistance:
            color = "#ef4444"  # 红色系
        else:
            color = "#10b981"  # 绿色系

        # 线条样式
        if strength >= 85:
            line_style = "solid"
            line_width = 3
            opacity = 0.95
        elif strength >= 70:
            line_style = "solid"
            line_width = 2
            opacity = 0.85
        elif strength >= 55:
            line_style = "dashed"
            line_width = 1.5
            opacity = 0.75
        else:
            line_style = "dotted"
            line_width = 1
            opacity = 0.6

        return {
            "color": color,
            "lineStyle": line_style,
            "lineWidth": line_width,
            "opacity": opacity
        }

    def _generate_analysis(self, current_price: float, levels: List[SRLevel]) -> SRAnalysis:
        """生成支撑压力分析"""
        if not levels:
            return SRAnalysis(
                summary="未检测到显著支撑压力位",
                dominant_trend="Neutral",
                price_position="Unknown"
            )

        # 分类支撑和压力
        supports = [l for l in levels if l.price < current_price]
        resistances = [l for l in levels if l.price > current_price]

        # 找最近的
        closest_support = max([l.price for l in supports]) if supports else None
        closest_resistance = min([l.price for l in resistances]) if resistances else None

        # 找最强的
        strongest_support = max(supports, key=lambda x: x.strength) if supports else None
        strongest_resistance = max(resistances, key=lambda x: x.strength) if resistances else None

        # 位置分析
        if closest_support and closest_resistance:
            range_size = closest_resistance - closest_support
            position_in_range = (current_price - closest_support) / range_size if range_size > 0 else 0.5

            if position_in_range < 0.3:
                position_desc = f"接近支撑区 ({closest_support:.2f})"
                trend_bias = "看涨"
            elif position_in_range > 0.7:
                position_desc = f"接近压力区 ({closest_resistance:.2f})"
                trend_bias = "承压"
            else:
                position_desc = f"区间中部 ({closest_support:.2f} - {closest_resistance:.2f})"
                trend_bias = "震荡"
        elif closest_support:
            position_desc = f"突破压力，支撑在 {closest_support:.2f}"
            trend_bias = "强势"
        elif closest_resistance:
            position_desc = f"跌破支撑，压力在 {closest_resistance:.2f}"
            trend_bias = "弱势"
        else:
            position_desc = "无明确支撑压力"
            trend_bias = "Neutral"

        # 构建摘要
        summary_parts = [f"检测到 {len(levels)} 个关键位"]

        # 统计 S/A 级别
        s_count = sum(1 for l in levels if l.rating == SRRating.S)
        a_count = sum(1 for l in levels if l.rating == SRRating.A)
        if s_count > 0:
            summary_parts.append(f"{s_count}个S级")
        if a_count > 0:
            summary_parts.append(f"{a_count}个A级")

        if strongest_support:
            rating_str = strongest_support.rating.value if hasattr(strongest_support.rating, 'value') else str(strongest_support.rating)
            summary_parts.append(f"最强支撑: {strongest_support.price:.2f} ({rating_str}级)")
        if strongest_resistance:
            rating_str = strongest_resistance.rating.value if hasattr(strongest_resistance.rating, 'value') else str(strongest_resistance.rating)
            summary_parts.append(f"最强压力: {strongest_resistance.price:.2f} ({rating_str}级)")

        return SRAnalysis(
            summary="，".join(summary_parts),
            dominant_trend=trend_bias,
            closest_support=closest_support,
            closest_resistance=closest_resistance,
            price_position=position_desc
        )
