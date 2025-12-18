#!/usr/bin/env python3
"""
历史数据回填脚本

用途:
- 下载并存储中证1000成分股的30天历史数据
- 支持断点续传
- 数据质量校验

用法:
    # 测试模式 (5只股票)
    python scripts/backfill_historical.py --test
    
    # 完整回填
    python scripts/backfill_historical.py --days 30
    
    # 指定股票
    python scripts/backfill_historical.py --symbol 000001
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_csi1000_constituents() -> List[str]:
    """
    获取中证1000成分股列表
    
    使用 AkShare 免费接口获取
    """
    try:
        import akshare as ak
        
        logger.info("正在获取中证1000成分股...")
        df = ak.index_stock_cons_csindex(symbol="000852")  # 中证1000代码
        
        if df is not None and not df.empty:
            # 获取股票代码列
            symbols = df['成分券代码'].tolist() if '成分券代码' in df.columns else df.iloc[:, 0].tolist()
            symbols = [str(s)[:6] for s in symbols]  # 只取前6位
            logger.info(f"获取到 {len(symbols)} 只中证1000成分股")
            return symbols
    except Exception as e:
        logger.warning(f"获取中证1000失败: {e}")
    
    # 备选：使用沪深300
    try:
        import akshare as ak
        
        logger.info("尝试获取沪深300成分股...")
        df = ak.index_stock_cons_csindex(symbol="000300")  # 沪深300代码
        
        if df is not None and not df.empty:
            symbols = df['成分券代码'].tolist() if '成分券代码' in df.columns else df.iloc[:, 0].tolist()
            symbols = [str(s)[:6] for s in symbols]
            logger.info(f"获取到 {len(symbols)} 只沪深300成分股")
            return symbols
    except Exception as e:
        logger.warning(f"获取沪深300也失败: {e}")
    
    # 最终备选：常用测试股票
    logger.warning("使用默认测试股票列表")
    return [
        '000001', '000002', '000063', '000100', '000157',
        '000333', '000538', '000651', '000661', '000725',
        '600000', '600036', '600276', '600519', '600887',
        '601318', '601398', '601988', '603288', '688981',
    ]


def backfill_single_stock(
    symbol: str,
    days: int = 30,
    data_manager = None,
    checkpoint_manager = None,
    force: bool = False  # 新增：强制回填
) -> Dict:
    """
    回填单只股票的历史数据
    
    Returns:
        Dict with status and stats
    """
    from signal_api.core.quant.data.checkpoint_manager import SyncStatus
    
    result = {
        'symbol': symbol,
        'status': 'pending',
        'minute_bars': 0,
        'daily_bars': 0,
        'error': None
    }
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    try:
        # 检查是否已完成 (除非强制回填)
        if checkpoint_manager and not force:
            existing = checkpoint_manager.get_progress(symbol, today)
            if existing and existing.status == SyncStatus.COMPLETED:
                logger.debug(f"跳过 {symbol}: 今日已完成")
                result['status'] = 'skipped'
                return result
            
            # 标记为进行中
            checkpoint_manager.save_progress(
                symbol, today, SyncStatus.IN_PROGRESS,
                minute_bars=0, daily_bars=0, completeness=0
            )
        
        # 获取日线数据
        logger.info(f"回填 {symbol} 日线数据 ({days}天)...")
        daily_df = data_manager.get_daily(symbol, days=days)
        daily_bars = len(daily_df) if daily_df is not None else 0
        result['daily_bars'] = daily_bars
        
        # 获取分钟线数据 (只获取最近1天，历史分钟线受API限制)
        logger.info(f"回填 {symbol} 分钟线数据 (1天)...")
        minute_df = data_manager.get_minute(symbol, days=1, freq='1min')
        minute_bars = len(minute_df) if minute_df is not None else 0
        result['minute_bars'] = minute_bars
        
        # 计算完整度
        expected_daily = int(days * 22 / 30)  # 约22交易日/月
        completeness = (daily_bars / expected_daily * 100) if expected_daily > 0 else 0
        
        # 更新检查点
        if checkpoint_manager:
            status = SyncStatus.COMPLETED if completeness >= 80 else SyncStatus.PARTIAL
            checkpoint_manager.save_progress(
                symbol, today, status,
                minute_bars=minute_bars,
                daily_bars=daily_bars,
                completeness=min(100, completeness)
            )
        
        result['status'] = 'completed' if completeness >= 80 else 'partial'
        logger.info(f"  ✅ {symbol}: 日线{daily_bars}条, 分钟线{minute_bars}条")
        
    except Exception as e:
        logger.error(f"  ❌ {symbol} 失败: {e}")
        result['status'] = 'failed'
        result['error'] = str(e)
        
        if checkpoint_manager:
            checkpoint_manager.save_progress(
                symbol, today, SyncStatus.FAILED,
                error_message=str(e)
            )
    
    return result


def run_backfill(
    symbols: Optional[List[str]] = None,
    days: int = 30,
    test_mode: bool = False,
    delay: float = 0.5,  # 请求间隔(秒)
    force: bool = False  # 强制回填
):
    """
    运行批量回填
    """
    from signal_api.core.quant.data.manager import DataManager, DataManagerConfig
    from signal_api.core.quant.data.checkpoint_manager import get_checkpoint_manager
    
    print("=" * 60)
    print("历史数据回填工具")
    print("=" * 60)
    
    # 初始化
    token = os.environ.get('TUSHARE_TOKEN')
    if not token:
        print("⚠️ TUSHARE_TOKEN 未配置，将使用 AkShare")
    
    config = DataManagerConfig(tushare_token=token)
    dm = DataManager(config)
    cm = get_checkpoint_manager()
    
    # 获取股票列表
    if symbols is None:
        symbols = get_csi1000_constituents()
    
    if test_mode:
        symbols = symbols[:5]
        print(f"\n🔬 测试模式: 只处理 {len(symbols)} 只股票")
    
    print(f"\n📊 待回填股票: {len(symbols)} 只")
    print(f"📅 回填天数: {days} 天")
    print(f"⏱️  预估时间: {len(symbols) * 2 * delay / 60:.1f} 分钟")
    print()
    
    # 统计
    stats = {
        'total': len(symbols),
        'completed': 0,
        'partial': 0,
        'failed': 0,
        'skipped': 0,
        'total_daily_bars': 0,
        'total_minute_bars': 0,
    }
    
    start_time = time.time()
    
    for i, symbol in enumerate(symbols):
        # 进度显示
        progress = (i + 1) / len(symbols) * 100
        elapsed = time.time() - start_time
        eta = (elapsed / (i + 1)) * (len(symbols) - i - 1) if i > 0 else 0
        
        print(f"[{i+1}/{len(symbols)}] {progress:.1f}% - ETA: {eta/60:.1f}分钟", end='\r')
        
        # 回填
        result = backfill_single_stock(symbol, days, dm, cm, force)
        
        # 统计
        stats[result['status']] = stats.get(result['status'], 0) + 1
        stats['total_daily_bars'] += result['daily_bars']
        stats['total_minute_bars'] += result['minute_bars']
        
        # 控制频率
        time.sleep(delay)
    
    # 最终统计
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("回填完成!")
    print("=" * 60)
    print(f"\n📊 统计:")
    print(f"   总计: {stats['total']} 只")
    print(f"   完成: {stats['completed']} 只")
    print(f"   部分: {stats['partial']} 只")
    print(f"   失败: {stats['failed']} 只")
    print(f"   跳过: {stats['skipped']} 只")
    print(f"\n📈 数据量:")
    print(f"   日线: {stats['total_daily_bars']} 条")
    print(f"   分钟线: {stats['total_minute_bars']} 条")
    print(f"\n⏱️  耗时: {elapsed/60:.1f} 分钟")
    print()
    
    # 显示检查点统计
    checkpoint_stats = cm.get_stats()
    print(f"📋 检查点统计:")
    print(f"   完成率: {checkpoint_stats.get('completion_rate', 0):.1f}%")
    
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="历史数据回填工具")
    parser.add_argument("--test", action="store_true", help="测试模式(5只股票)")
    parser.add_argument("--days", type=int, default=30, help="回填天数")
    parser.add_argument("--symbol", type=str, help="指定单只股票")
    parser.add_argument("--delay", type=float, default=0.5, help="请求间隔(秒)")
    parser.add_argument("--force", action="store_true", help="强制回填(不跳过已完成)")
    
    args = parser.parse_args()
    
    symbols = [args.symbol] if args.symbol else None
    
    run_backfill(
        symbols=symbols,
        days=args.days,
        test_mode=args.test,
        delay=args.delay,
        force=args.force
    )
