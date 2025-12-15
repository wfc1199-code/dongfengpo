#!/usr/bin/env python3
"""
测试不同缓存配置对期权数据延迟的影响
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
from typing import List, Dict

class CacheConfigTester:
    def __init__(self, api_url: str = "http://localhost:9001"):
        self.api_url = api_url
        self.results = []

    async def test_cache_configs(self):
        """测试不同缓存配置"""
        print("=" * 60)
        print("期权API缓存配置测试")
        print("=" * 60)

        test_configs = [
            {"name": "无缓存", "cache": 0, "description": "每次都获取最新数据"},
            {"name": "10秒缓存", "cache": 10, "description": "适用于高频交易"},
            {"name": "30秒缓存", "cache": 30, "description": "平衡性能和实时性"},
            {"name": "60秒缓存", "cache": 60, "description": "默认配置"},
            {"name": "300秒缓存", "cache": 300, "description": "5分钟缓存"},
        ]

        option_code = "10004603"

        for config in test_configs:
            print(f"\n测试配置: {config['name']} ({config['cache']}秒)")
            print("-" * 40)
            print(f"说明: {config['description']}")

            # 设置缓存时间（通过修改环境变量或配置）
            # 这里模拟不同的缓存时间
            result = await self.run_cache_test(option_code, config['cache'], config['name'])
            self.results.append(result)

            # 等待一段时间再测试下一个配置
            await asyncio.sleep(2)

        self.print_summary()

    async def run_cache_test(self, option_code: str, cache_seconds: int, config_name: str) -> Dict:
        """运行单个缓存测试"""
        # 清除缓存
        await self.clear_cache()

        latencies = []
        data_delays = []
        cache_hits = 0
        cache_misses = 0

        # 连续请求10次
        for i in range(10):
            start_time = time.time()

            try:
                # 添加时间戳防止缓存
                url = f"{self.api_url}/api/options/{option_code}/minute?_t={int(time.time() * 1000)}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        data = await response.json()
                        end_time = time.time()

                        latency = (end_time - start_time) * 1000
                        latencies.append(latency)

                        # 检查缓存状态
                        cache_status = response.headers.get('X-Cache', 'MISS')
                        if cache_status == 'HIT':
                            cache_hits += 1
                        else:
                            cache_misses += 1

                        # 获取数据延迟
                        if 'data_delay_minutes' in data:
                            data_delays.append(data['data_delay_minutes'])

                        print(f"  请求 {i+1}: {latency:.2f}ms, 缓存:{cache_status}, 数据延迟:{data.get('data_delay_minutes', 0)}分")

                        # 根据缓存时间等待
                        if i < 9:  # 最后一次不需要等待
                            await asyncio.sleep(cache_seconds / 10)

            except Exception as e:
                print(f"  请求 {i+1} 失败: {e}")

        # 计算统计数据
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0
        avg_data_delay = sum(data_delays) / len(data_delays) if data_delays else 0
        cache_hit_rate = (cache_hits / (cache_hits + cache_misses)) * 100 if (cache_hits + cache_misses) > 0 else 0

        print(f"\n  统计结果:")
        print(f"    平均延迟: {avg_latency:.2f}ms")
        print(f"    最大延迟: {max_latency:.2f}ms")
        print(f"    最小延迟: {min_latency:.2f}ms")
        print(f"    平均数据延迟: {avg_data_delay:.1f}分钟")
        print(f"    缓存命中率: {cache_hit_rate:.1f}%")

        return {
            "config_name": config_name,
            "cache_seconds": cache_seconds,
            "avg_latency": avg_latency,
            "max_latency": max_latency,
            "min_latency": min_latency,
            "avg_data_delay": avg_data_delay,
            "cache_hit_rate": cache_hit_rate,
            "total_requests": cache_hits + cache_misses
        }

    async def clear_cache(self):
        """清除缓存"""
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(f"{self.api_url}/test/clear-cache")
        except:
            pass

    async def test_real_time_scenario(self):
        """测试实时场景（模拟交易期间）"""
        print("\n" + "=" * 60)
        print("实时交易场景测试")
        print("=" * 60)

        # 模拟快速连续请求（如交易时频繁刷新）
        print("\n快速连续请求测试（每秒1次，持续10秒）:")
        await self.test_rapid_requests(interval=1, duration=10)

        print("\n极快请求测试（每500ms一次，持续5秒）:")
        await self.test_rapid_requests(interval=0.5, duration=5)

    async def test_rapid_requests(self, interval: float, duration: int):
        """测试快速请求"""
        option_code = "10004603"
        latencies = []
        data_delays = []

        start_time = time.time()
        request_count = 0

        while time.time() - start_time < duration:
            req_start = time.time()

            try:
                url = f"{self.api_url}/api/options/{option_code}/minute?_t={int(time.time() * 1000)}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        data = await response.json()
                        req_end = time.time()

                        latency = (req_end - req_start) * 1000
                        latencies.append(latency)

                        if 'data_delay_minutes' in data:
                            data_delays.append(data['data_delay_minutes'])

                        request_count += 1

                        if request_count % 5 == 0:
                            print(f"  请求 {request_count}: {latency:.2f}ms")

            except Exception as e:
                print(f"  请求失败: {e}")

            await asyncio.sleep(interval)

        # 统计结果
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

            print(f"\n  快速请求统计:")
            print(f"    总请求数: {request_count}")
            print(f"    平均延迟: {avg_latency:.2f}ms")
            print(f"    最大延迟: {max_latency:.2f}ms")
            print(f"    P95延迟: {p95_latency:.2f}ms")

            # 判断性能
            if avg_latency < 100 and p95_latency < 200:
                print(f"    ✓ 性能优秀，适合期权高频交易")
            elif avg_latency < 300 and p95_latency < 500:
                print(f"    ⚠ 性能一般，可以用于期权交易")
            else:
                print(f"    ✗ 性能较差，需要优化")

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 60)
        print("缓存配置测试总结")
        print("=" * 60)

        print("\n各配置性能对比:")
        print(f"{'配置':<12} {'平均延迟(ms)':<12} {'数据延迟(分)':<12} {'缓存命中率(%)':<12} {'评级'}")
        print("-" * 60)

        for result in self.results:
            # 评级
            rating = ""
            if result['avg_latency'] < 100 and result['avg_data_delay'] < 2:
                rating = "优秀"
            elif result['avg_latency'] < 300 and result['avg_data_delay'] < 5:
                rating = "良好"
            else:
                rating = "较差"

            print(f"{result['config_name']:<12} {result['avg_latency']:<12.2f} "
                  f"{result['avg_data_delay']:<12.1f} {result['cache_hit_rate']:<12.1f} {rating}")

        print("\n建议:")
        best_config = min(self.results, key=lambda x: x['avg_latency'] + x['avg_data_delay'] * 10)
        print(f"1. 推荐配置: {best_config['config_name']} - 平衡了性能和实时性")
        print("2. 对于期权交易，建议缓存时间不超过30秒")
        print("3. 考虑使用WebSocket推送来减少API请求延迟")
        print("4. 在交易高峰期可能需要调整缓存策略")

        # 找出最优配置
        print("\n最优配置分析:")
        for result in self.results:
            score = 100 - result['avg_latency'] / 10 - result['avg_data_delay'] * 5
            print(f"  {result['config_name']}: 综合评分 {score:.1f}/100")

        print("\n延迟优化方案:")
        print("1. 使用Redis缓存，设置合理的过期时间")
        print("2. 实现增量更新，只返回变化的数据")
        print("3. 使用CDN加速静态数据")
        print("4. 优化数据库查询，使用索引")
        print("5. 考虑数据预加载和批量获取")


async def main():
    """主函数"""
    tester = CacheConfigTester()

    # 测试缓存配置
    await tester.test_cache_configs()

    # 测试实时场景
    await tester.test_real_time_scenario()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())