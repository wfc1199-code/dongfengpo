from typing import List, Optional, Tuple, Dict
import numpy as np
from collections import defaultdict
from .models import SRLevel, SRType, SRRating, SRSource

class TDXEngine:
    """
    Level 2 & 3: 动态统计与 TDX 风格算法
    核心逻辑：
    1. 识别局部高低点 (Fractals/Pivots)
    2. 对高低点进行聚类 (Clustering)
    3. 根据触及次数、成交量、时间衰减计算强度
    """

    def calculate(self,
                  prices: List[float],
                  highs: Optional[List[float]],
                  lows: Optional[List[float]],
                  volumes: Optional[List[float]] = None,
                  timestamps: Optional[List[int]] = None) -> List[SRLevel]:

        if not prices or len(prices) < 10:
            return []

        # 准备数据
        p_highs = np.array(highs if highs else prices)
        p_lows = np.array(lows if lows else prices)
        p_vols = np.array(volumes) if volumes else np.ones(len(prices))

        # 1. 识别局部高低点 (Pivots)
        # 窗口大小：前后各看 5 根 K 线
        window = 5
        pivot_highs = self._find_pivots(p_highs, window, is_high=True)
        pivot_lows = self._find_pivots(p_lows, window, is_high=False)

        # 2. 聚类合并 (Clustering)
        # 将价格接近的点合并。阈值为价格的 0.5%
        clusters = self._cluster_pivots(pivot_highs, pivot_lows, p_vols, threshold_pct=0.005)

        # 3. 转换为 SRLevel 对象
        levels = []
        current_price = prices[-1]

        for cluster in clusters:
            # 基础强度计算
            # 基础分 50 + 次数 * 10 + 成交量加成
            strength = 50 + (cluster['count'] - 1) * 10

            # 成交量加成 (归一化后的相对量)
            avg_vol_ratio = cluster['avg_vol'] / (np.mean(p_vols) if len(p_vols) > 0 else 1)
            if avg_vol_ratio > 1.5:
                strength += 10
            if avg_vol_ratio > 3.0:
                strength += 10

            # 时间衰减：最近的点权重更高 (简单模拟)
            # 这里暂时不做的太复杂

            strength = min(strength, 95) # 上限 95

            # 评级
            rating = SRRating.C
            if strength >= 85: rating = SRRating.S
            elif strength >= 75: rating = SRRating.A
            elif strength >= 60: rating = SRRating.B

            # 类型判断
            # 如果当前价格在下方，则是阻力；在上方，则是支撑
            # 但实际上我们应该保留它是“作为高点形成的”还是“低点形成的”这一属性
            # 简化起见，按相对位置动态判断，或者混合

            # 这里的逻辑是：如果是基于 High 形成的 cluster，倾向于 Resistance
            # 如果是基于 Low 形成的 cluster，倾向于 Support
            # 如果混合，看哪个多

            sr_type = SRType.RESISTANCE
            if cluster['source_type'] == 'low':
                sr_type = SRType.SUPPORT
            elif cluster['source_type'] == 'mixed':
                sr_type = SRType.RESISTANCE if cluster['price'] > current_price else SRType.SUPPORT

            # 视觉样式
            color = "#f87171" if sr_type == SRType.RESISTANCE else "#34d399"

            levels.append(SRLevel(
                price=round(cluster['price'], 3),
                type=sr_type,
                strength=round(strength, 1),
                rating=rating,
                source=[SRSource.TDX, SRSource.DYNAMIC],
                visual_style={
                    "color": color,
                    "lineStyle": "solid",
                    "lineWidth": 1 + (strength/100)*2, # 越强越粗
                    "opacity": strength/100
                },
                description=f"TDX聚类(触及{cluster['count']}次)"
            ))

        # 选取最强的 N 个，避免线条过多
        levels.sort(key=lambda x: x.strength, reverse=True)
        return levels[:5] # 只返回最强的 5 条

    def _find_pivots(self, data: np.ndarray, window: int, is_high: bool) -> List[Dict]:
        """
        寻找局部极值点
        """
        pivots = []
        n = len(data)

        for i in range(window, n - window):
            segment = data[i-window : i+window+1]
            current = data[i]

            if is_high:
                if current == max(segment):
                    pivots.append({'index': i, 'price': current, 'type': 'high'})
            else:
                if current == min(segment):
                    pivots.append({'index': i, 'price': current, 'type': 'low'})

        return pivots

    def _cluster_pivots(self, highs: List[Dict], lows: List[Dict], volumes: np.ndarray, threshold_pct: float) -> List[Dict]:
        """
        简单的聚类算法
        """
        all_points = highs + lows
        if not all_points:
            return []

        # 按价格排序
        all_points.sort(key=lambda x: x['price'])

        clusters = []
        if not all_points:
            return []

        current_cluster = {
            'prices': [all_points[0]['price']],
            'vols': [volumes[all_points[0]['index']]],
            'types': [all_points[0]['type']]
        }

        for i in range(1, len(all_points)):
            point = all_points[i]
            prev_price = current_cluster['prices'][-1] # 用最后一个加入的，或者用平均值
            avg_cluster_price = sum(current_cluster['prices']) / len(current_cluster['prices'])

            # 检查是否在阈值内
            if abs(point['price'] - avg_cluster_price) / avg_cluster_price <= threshold_pct:
                current_cluster['prices'].append(point['price'])
                current_cluster['vols'].append(volumes[point['index']])
                current_cluster['types'].append(point['type'])
            else:
                # 结束当前聚类，保存
                clusters.append(self._finalize_cluster(current_cluster))
                # 开启新聚类
                current_cluster = {
                    'prices': [point['price']],
                    'vols': [volumes[point['index']]],
                    'types': [point['type']]
                }

        # 添加最后一个
        clusters.append(self._finalize_cluster(current_cluster))

        return clusters

    def _finalize_cluster(self, cluster_data: Dict) -> Dict:
        count = len(cluster_data['prices'])
        avg_price = sum(cluster_data['prices']) / count
        avg_vol = sum(cluster_data['vols']) / count

        high_count = cluster_data['types'].count('high')
        low_count = cluster_data['types'].count('low')

        source_type = 'mixed'
        if high_count > 0 and low_count == 0:
            source_type = 'high'
        elif low_count > 0 and high_count == 0:
            source_type = 'low'

        return {
            'price': avg_price,
            'count': count,
            'avg_vol': avg_vol,
            'source_type': source_type
        }
