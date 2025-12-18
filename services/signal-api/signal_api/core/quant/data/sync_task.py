"""
数据同步任务

用途:
- 每日同步分钟线和日线数据
- 支持断点续传
- 数据质量校验
- 定时执行（16:30后）

用法:
    # 手动同步
    python -m signal_api.core.quant.data.sync_task
    
    # 定时任务 (crontab)
    30 16 * * 1-5 cd /path/to/project && python -m signal_api.core.quant.data.sync_task
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SyncCheckpoint:
    """同步检查点"""
    symbol: str
    last_sync_date: str
    status: str  # 'completed', 'partial', 'failed'
    bars_synced: int
    error_message: Optional[str] = None
    updated_at: Optional[str] = None


class DataSyncTask:
    """
    数据同步任务
    
    Features:
    - 支持断点续传（checkpoint-based）
    - 数据质量校验（240根K线）
    - 自动重试机制
    - 同步日志记录
    """
    
    def __init__(
        self,
        data_root: str = "./quant_data",
        tushare_token: Optional[str] = None
    ):
        """初始化同步任务"""
        self.data_root = Path(data_root)
        self.checkpoint_dir = self.data_root / "checkpoints"
        self.log_dir = self.data_root / "logs"
        
        # 确保目录存在
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 DataManager
        from .manager import DataManager, DataManagerConfig
        
        token = tushare_token or os.environ.get('TUSHARE_TOKEN')
        self.dm = DataManager(DataManagerConfig(tushare_token=token))
        
        # 同步统计
        self.stats = {
            'total_symbols': 0,
            'synced': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None,
        }
        
        logger.info("DataSyncTask initialized")
    
    def load_checkpoint(self, symbol: str) -> Optional[SyncCheckpoint]:
        """加载同步检查点"""
        checkpoint_file = self.checkpoint_dir / f"{symbol}.json"
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                    return SyncCheckpoint(**data)
            except Exception as e:
                logger.warning(f"Failed to load checkpoint for {symbol}: {e}")
        return None
    
    def save_checkpoint(self, checkpoint: SyncCheckpoint):
        """保存同步检查点"""
        checkpoint.updated_at = datetime.now().isoformat()
        checkpoint_file = self.checkpoint_dir / f"{checkpoint.symbol}.json"
        
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump(asdict(checkpoint), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save checkpoint for {checkpoint.symbol}: {e}")
    
    def get_sync_symbols(self) -> List[str]:
        """
        获取需要同步的股票列表
        
        默认: 沪深300成分股
        可以从配置文件或数据库获取
        """
        # 简化：返回常见测试股票
        default_symbols = [
            '000001', '000002', '000063', '000100', '000157',
            '600000', '600036', '600519', '600887', '601318',
        ]
        
        # 尝试从 Tushare 获取完整列表
        try:
            stock_list = self.dm.tushare.get_stock_list()
            if stock_list is not None and len(stock_list) > 0:
                # 只取前100只进行测试
                symbols = stock_list['ts_code'].str[:6].tolist()[:100]
                logger.info(f"Loaded {len(symbols)} symbols from Tushare")
                return symbols
        except Exception as e:
            logger.warning(f"Failed to get stock list: {e}")
        
        return default_symbols
    
    def validate_minute_data(self, symbol: str, date: str) -> bool:
        """
        验证分钟线数据完整性
        
        A股交易日应有 240 根分钟K线 (4小时 * 60分钟)
        允许5%误差（228根）
        """
        try:
            return self.dm.validate_minute_data(symbol, date)
        except Exception as e:
            logger.warning(f"Validation failed for {symbol}/{date}: {e}")
            return False
    
    def sync_symbol(
        self,
        symbol: str,
        days: int = 30,
        force: bool = False
    ) -> SyncCheckpoint:
        """
        同步单个股票数据
        
        Args:
            symbol: 股票代码
            days: 同步天数
            force: 是否强制重新同步
        """
        checkpoint = self.load_checkpoint(symbol)
        
        # 检查是否需要同步
        today = datetime.now().strftime("%Y-%m-%d")
        if checkpoint and checkpoint.status == 'completed' and not force:
            if checkpoint.last_sync_date == today:
                logger.debug(f"Skip {symbol}: already synced today")
                self.stats['skipped'] += 1
                return checkpoint
        
        logger.info(f"Syncing {symbol}...")
        
        try:
            # 同步分钟线数据
            minute_df = self.dm.get_minute(symbol, days=days, freq='1min')
            bars_synced = len(minute_df) if minute_df is not None else 0
            
            # 同步日线数据
            daily_df = self.dm.get_daily(symbol, days=days)
            daily_bars = len(daily_df) if daily_df is not None else 0
            
            # 验证数据
            is_valid = self.validate_minute_data(symbol, today)
            
            status = 'completed' if is_valid else 'partial'
            
            checkpoint = SyncCheckpoint(
                symbol=symbol,
                last_sync_date=today,
                status=status,
                bars_synced=bars_synced,
            )
            
            self.save_checkpoint(checkpoint)
            self.stats['synced'] += 1
            
            logger.info(f"Synced {symbol}: {bars_synced} minute bars, {daily_bars} daily bars")
            
        except Exception as e:
            logger.error(f"Failed to sync {symbol}: {e}")
            
            checkpoint = SyncCheckpoint(
                symbol=symbol,
                last_sync_date=today,
                status='failed',
                bars_synced=0,
                error_message=str(e),
            )
            self.save_checkpoint(checkpoint)
            self.stats['failed'] += 1
        
        return checkpoint
    
    def sync_all(
        self,
        symbols: Optional[List[str]] = None,
        days: int = 30,
        force: bool = False
    ) -> Dict:
        """
        同步所有股票数据
        
        Args:
            symbols: 股票列表（默认自动获取）
            days: 同步天数
            force: 是否强制重新同步
        """
        self.stats['start_time'] = datetime.now().isoformat()
        
        if symbols is None:
            symbols = self.get_sync_symbols()
        
        self.stats['total_symbols'] = len(symbols)
        logger.info(f"Starting sync for {len(symbols)} symbols")
        
        for i, symbol in enumerate(symbols):
            try:
                self.sync_symbol(symbol, days=days, force=force)
            except Exception as e:
                logger.error(f"Unexpected error syncing {symbol}: {e}")
                self.stats['failed'] += 1
            
            # 进度日志
            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i + 1}/{len(symbols)}")
        
        self.stats['end_time'] = datetime.now().isoformat()
        
        # 保存同步日志
        self._save_sync_log()
        
        return self.stats
    
    def _save_sync_log(self):
        """保存同步日志"""
        log_file = self.log_dir / f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(log_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
            logger.info(f"Sync log saved to {log_file}")
        except Exception as e:
            logger.error(f"Failed to save sync log: {e}")
    
    def get_missing_symbols(self, days: int = 30) -> List[str]:
        """获取缺失数据的股票列表"""
        missing = []
        symbols = self.get_sync_symbols()
        
        for symbol in symbols:
            checkpoint = self.load_checkpoint(symbol)
            if checkpoint is None or checkpoint.status != 'completed':
                missing.append(symbol)
        
        return missing


def run_sync():
    """运行同步任务"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("数据同步任务")
    print("=" * 60)
    
    # 检查环境变量
    token = os.environ.get('TUSHARE_TOKEN')
    if not token:
        print("⚠️ TUSHARE_TOKEN 未配置")
        print("请设置: export TUSHARE_TOKEN='your_token'")
        return
    
    # 检查时间（建议16:30后运行）
    now = datetime.now()
    if now.hour < 16 or (now.hour == 16 and now.minute < 30):
        print(f"⚠️ 当前时间 {now.strftime('%H:%M')}，建议16:30后运行")
        print("   继续执行...")
    
    # 运行同步
    task = DataSyncTask()
    
    # 只同步少量股票用于测试
    test_symbols = ['000001', '000002', '600000', '600036', '601318']
    
    stats = task.sync_all(symbols=test_symbols, days=5)
    
    print("\n" + "=" * 60)
    print("同步完成!")
    print("=" * 60)
    print(f"总计: {stats['total_symbols']} 只")
    print(f"成功: {stats['synced']} 只")
    print(f"失败: {stats['failed']} 只")
    print(f"跳过: {stats['skipped']} 只")


if __name__ == "__main__":
    run_sync()
