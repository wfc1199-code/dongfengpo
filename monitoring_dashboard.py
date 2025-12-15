#!/usr/bin/env python3
"""
东风破量化交易系统 - 监控仪表板

实时监控所有微服务的健康状态、性能指标和数据流
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
import redis.asyncio as aioredis


class ServiceMonitor:
    """服务监控器"""

    def __init__(self):
        self.services = {
            "Signal-API": {"url": "http://localhost:8000/health", "port": 8000},
            "Backtest-Service": {"url": "http://localhost:8200/health", "port": 8200},
            "API Gateway": {"url": "http://localhost:8888/gateway/health", "port": 8888},
            "Signal-Streamer": {"url": "http://localhost:8100/health", "port": 8100},
        }
        self.redis_client: Optional[aioredis.Redis] = None

    async def init_redis(self):
        """初始化Redis连接"""
        self.redis_client = await aioredis.from_url(
            "redis://localhost:6379",
            decode_responses=True
        )

    async def check_service(self, name: str, info: Dict) -> Dict:
        """检查单个服务健康状态"""
        result = {
            "name": name,
            "status": "unknown",
            "response_time": None,
            "error": None
        }

        try:
            start = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(info["url"], timeout=aiohttp.ClientTimeout(total=2)) as response:
                    elapsed = (time.time() - start) * 1000  # ms
                    result["response_time"] = round(elapsed, 2)
                    result["status"] = "healthy" if response.status == 200 else "unhealthy"
        except asyncio.TimeoutError:
            result["status"] = "timeout"
            result["error"] = "请求超时"
        except aiohttp.ClientConnectorError:
            result["status"] = "down"
            result["error"] = "无法连接"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def check_redis_health(self) -> Dict:
        """检查Redis健康状态"""
        if not self.redis_client:
            return {"status": "not_initialized"}

        try:
            start = time.time()
            await self.redis_client.ping()
            elapsed = (time.time() - start) * 1000

            # 获取Redis信息
            info = await self.redis_client.info("stats")

            return {
                "status": "healthy",
                "response_time": round(elapsed, 2),
                "total_commands": info.get("total_commands_processed", 0),
                "connected_clients": info.get("connected_clients", 0)
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def get_stream_stats(self) -> Dict:
        """获取Redis Stream统计数据"""
        if not self.redis_client:
            return {}

        streams = {
            "clean_ticks": "dfp:clean_ticks",
            "strategy_signals": "dfp:strategy_signals",
            "opportunities": "dfp:opportunities"
        }

        stats = {}
        for name, stream_key in streams.items():
            try:
                length = await self.redis_client.xlen(stream_key)
                stats[name] = length
            except:
                stats[name] = 0

        return stats

    async def monitor_loop(self):
        """监控循环"""
        await self.init_redis()

        print("\n" + "="*80)
        print("🚀 东风破量化交易系统 - 实时监控仪表板")
        print("="*80)
        print()

        iteration = 0

        try:
            while True:
                iteration += 1
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                print(f"\n⏰ 监控时间: {timestamp} (第 {iteration} 次检查)")
                print("-" * 80)

                # 检查所有HTTP服务
                print("\n📊 HTTP 服务健康检查:")
                tasks = [self.check_service(name, info) for name, info in self.services.items()]
                results = await asyncio.gather(*tasks)

                for result in results:
                    status_icon = {
                        "healthy": "✅",
                        "unhealthy": "⚠️",
                        "down": "❌",
                        "timeout": "⏱️",
                        "error": "🔴",
                        "unknown": "❓"
                    }.get(result["status"], "❓")

                    name_padded = result["name"].ljust(20)
                    status_padded = result["status"].ljust(12)

                    if result["response_time"]:
                        print(f"   {status_icon} {name_padded} {status_padded} ({result['response_time']}ms)")
                    else:
                        error_msg = result.get("error", "未知错误")
                        print(f"   {status_icon} {name_padded} {status_padded} ({error_msg})")

                # 检查Redis
                print("\n📦 Redis 状态:")
                redis_health = await self.check_redis_health()
                if redis_health["status"] == "healthy":
                    print(f"   ✅ Redis                运行正常         ({redis_health['response_time']}ms)")
                    print(f"      - 已处理命令数: {redis_health.get('total_commands', 0):,}")
                    print(f"      - 连接客户端数: {redis_health.get('connected_clients', 0)}")
                else:
                    print(f"   ❌ Redis                状态异常         ({redis_health.get('error', '未知错误')})")

                # 检查后台服务（通过Redis判断）
                print("\n🔧 后台服务状态:")
                background_services = [
                    ("Feature-Pipeline", "feature-pipeline", "dfp:clean_ticks"),
                    ("Strategy-Engine", "strategy-engine", "dfp:features"),
                    ("Opportunity-Aggregator", "opportunity-aggregator", "dfp:strategy_signals"),
                    ("Risk-Guard", "risk-guard", "dfp:opportunities")
                ]

                for service_name, consumer_group, stream_name in background_services:
                    try:
                        # 检查消费者组信息
                        groups = await self.redis_client.xinfo_groups(stream_name)
                        service_found = False

                        for group in groups:
                            if group['name'] == consumer_group:
                                service_found = True
                                consumers = group['consumers']
                                pending = group['pending']

                                status_icon = "✅" if consumers > 0 else "⚠️"
                                name_padded = service_name.ljust(25)

                                print(f"   {status_icon} {name_padded} {consumers} 消费者, {pending} 待处理")
                                break

                        if not service_found:
                            print(f"   ❌ {service_name.ljust(25)} 消费者组不存在")
                    except Exception as e:
                        print(f"   ❓ {service_name.ljust(25)} 无法检查 ({e})")

                # 数据流统计
                print("\n📈 数据流统计:")
                stream_stats = await self.get_stream_stats()
                for name, count in stream_stats.items():
                    print(f"   - {name.ljust(20)}: {count:,} 条消息")

                # 等待下一次检查
                print("\n" + "-" * 80)
                print("⏳ 10秒后进行下一次检查... (Ctrl+C 退出)")

                await asyncio.sleep(10)

        except KeyboardInterrupt:
            print("\n\n⏸️  监控已停止")
        finally:
            if self.redis_client:
                await self.redis_client.aclose()


async def main():
    """主函数"""
    monitor = ServiceMonitor()
    await monitor.monitor_loop()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     东风破量化交易系统 - 监控仪表板 v1.0                     ║
║                                                              ║
║     实时监控所有微服务的健康状态和性能指标                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()