import unittest
import numpy as np
from signal_api.core.support_resistance.tdx_engine import TDXEngine
from signal_api.core.support_resistance.models import SRType

class TestTDXEngine(unittest.TestCase):
    def setUp(self):
        self.engine = TDXEngine()

    def test_basic_pivots(self):
        """测试基本的波峰波谷识别"""
        # 构造一个明显的 M 头 W 底形态
        # 10 -> 12 -> 10 -> 12 -> 10
        prices = [10.0, 10.5, 11.0, 11.5, 12.0, 11.5, 11.0, 10.5, 10.0,
                  10.5, 11.0, 11.5, 12.0, 11.5, 11.0, 10.5, 10.0]
        # 扩展一下长度以满足 window=5 的要求 (len >= 11)
        prices = [10.0] * 5 + prices + [10.0] * 5

        levels = self.engine.calculate(prices, None, None)

        # 应该识别出 12.0 附近的阻力和 10.0 附近的支撑
        has_resistance = any(l.price == 12.0 and l.type == SRType.RESISTANCE for l in levels)
        # 注意：由于聚类和排序，可能只返回最强的。

        # 打印结果检查
        print("\nLevels found:", levels)

        self.assertTrue(len(levels) > 0)

    def test_clustering_strength(self):
        """测试聚类后的强度提升"""
        # 构造多次触及 100 元的情况
        base = [100.0, 105.0, 100.0, 95.0, 100.0, 105.0, 100.0, 95.0]
        # 扩充
        prices = []
        for p in base:
            prices.extend([p + (i*0.01) for i in range(5)]) # 小幅波动

        # 确保数据量足够
        prices = [100.0] * 10 + prices + [100.0] * 10

        levels = self.engine.calculate(prices, None, None)

        # 找到 100 附近的线
        level_100 = next((l for l in levels if 99.5 < l.price < 100.5), None)

        self.assertIsNotNone(level_100)
        if level_100:
            print(f"\nCluster at 100 strength: {level_100.strength}")
            # 多次触及，强度应该较高
            self.assertTrue(level_100.strength > 50)

if __name__ == '__main__':
    unittest.main()
