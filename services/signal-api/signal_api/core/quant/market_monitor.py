"""
市场监控模块 (Market Monitor)

职责:
1. 监控大盘指数 (上证指数) 实时状态
2. 统计市场情绪 (涨跌家数、涨停数)
3. 生成市场背景描述 (Market Context) 供 AI 复核使用
"""

import logging
from datetime import datetime
from typing import Dict, Optional
import akshare as ak

logger = logging.getLogger(__name__)

class MarketMonitor:
    """
    市场监控器
    
    维护最新的市场状态快照，供 AI Reviewer 使用
    """
    
    def __init__(self):
        self._last_update: Optional[datetime] = None
        self._context_cache: str = ""
        self._stats_cache: Dict = {}
        self._update_interval_seconds = 60  # 每分钟更新一次
        
    async def update(self):
        """更新市场数据 (非阻塞)"""
        now = datetime.now()
        
        # 简单限流: 如果距离上次更新不足间隔，跳过
        if self._last_update and (now - self._last_update).total_seconds() < self._update_interval_seconds:
            return

        try:
            # 运行在线程池中以免阻塞主循环
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._fetch_all_data)
            
            self._last_update = now
            logger.info(f"市场监控已更新: {self._context_cache[:30]}...")
            
        except Exception as e:
            logger.warning(f"市场监控更新失败: {e}")

    def get_context(self) -> str:
        """获取当前市场背景描述"""
        return self._context_cache

    def _fetch_all_data(self):
        """获取所有监控数据 (同步阻塞方法)"""
        try:
            # 1. 获取上证指数
            context_str = "市场背景:\n"
            
            # 使用 akshare 获取指数实时行情 (简化版: 假设akshare可用)
            # 注意: 实际生产中应使用更稳定的数据源或异常处理
            try:
                # 获取上证指数 (000001)
                df = ak.stock_zh_index_spot()
                sh_index = df[df['代码'] == 'sh000001'].iloc[0]
                
                price = sh_index['最新价']
                change_pct = sh_index['涨跌幅']
                amount = sh_index['成交额'] / 1e8
                
                status = "上涨" if change_pct > 0 else "下跌"
                if abs(change_pct) < 0.2: status = "震荡"
                if change_pct > 1.0: status = "大涨"
                if change_pct < -1.0: status = "大跌"
                
                context_str += f"- 上证指数: {price} ({change_pct:.2f}%), 状态: {status}, 成交: {amount:.0f}亿\n"
                
            except Exception as e:
                context_str += "- 上证指数: 获取失败\n"
            
            # 2. 获取全市场情绪 (简化: 涨跌家数)
            # 这里仅作示例，实际可调用 stock_zh_a_spot_em 获取全市场概览
            # 为节省流量，这里暂略
            
            # 更新缓存
            self._context_cache = context_str
            
        except Exception as e:
            logger.error(f"Fetch market data error: {e}")
