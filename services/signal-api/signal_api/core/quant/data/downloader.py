"""
AI Quant Platform - Data Downloader
Orchestrates data download from Tushare with validation and storage.

Features:
- Batch download with checkpoint/resume
- Automatic validation before storage
- Progress logging
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from .duckdb_manager import DuckDBManager
from .tushare_client import TushareClient
from .validator import DataValidator

logger = logging.getLogger(__name__)


class DataDownloader:
    """
    Orchestrates market data download workflow.
    
    Workflow:
    1. Get stock list from Tushare
    2. For each stock, download minute data
    3. Validate data quality
    4. Store valid data to DuckDB/Parquet
    5. Save checkpoint for resume
    """
    
    def __init__(
        self,
        db_manager: DuckDBManager,
        ts_client: TushareClient,
        validator: DataValidator
    ):
        self.db = db_manager
        self.ts = ts_client
        self.validator = validator
        
        logger.info("DataDownloader initialized")
    
    def download_minute_data(
        self,
        symbols: Optional[List[str]] = None,
        days: int = 30,
        freq: str = "1min"
    ) -> dict:
        """
        Download minute-level data for specified stocks.
        
        Args:
            symbols: List of stock symbols. If None, downloads all A-shares.
            days: Number of past days to download.
            freq: Data frequency ('1min', '5min', etc.)
        
        Returns:
            Summary dict with success/failure counts.
        """
        # Get symbol list if not provided
        if symbols is None:
            stock_list = self.ts.get_stock_list()
            symbols = stock_list['ts_code'].tolist()
            logger.info(f"Will download data for {len(symbols)} stocks")
        
        # Load checkpoint for resume
        checkpoint = self.ts.load_checkpoint() or {
            "completed": [],
            "failed": [],
            "start_time": datetime.now().isoformat()
        }
        completed = set(checkpoint.get("completed", []))
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        start_str = start_date.strftime("%Y-%m-%d 09:00:00")
        end_str = end_date.strftime("%Y-%m-%d 15:00:00")
        
        logger.info(f"Downloading {freq} data from {start_str} to {end_str}")
        
        # Download each symbol
        success_count = 0
        fail_count = 0
        
        for i, symbol in enumerate(symbols):
            # Skip if already completed
            if symbol in completed:
                logger.debug(f"Skipping {symbol} (already downloaded)")
                continue
            
            try:
                # Download data
                df = self.ts.get_minute_data(
                    ts_code=symbol,
                    start_date=start_str,
                    end_date=end_str,
                    freq=freq
                )
                
                if df.empty:
                    logger.warning(f"No data returned for {symbol}")
                    checkpoint["failed"].append(symbol)
                    fail_count += 1
                    continue
                
                # Validate data (non-strict mode - log warnings but continue)
                is_valid, errors = self.validator.validate(df, symbol)
                
                if not is_valid:
                    logger.warning(f"Validation warnings for {symbol}: {len(errors)} issues")
                    # Still save data but log the issues
                
                # Save to DuckDB/Parquet
                if self.db.save_minute_data(symbol, df):
                    completed.add(symbol)
                    checkpoint["completed"] = list(completed)
                    success_count += 1
                else:
                    checkpoint["failed"].append(symbol)
                    fail_count += 1
                
                # Save checkpoint periodically
                if (i + 1) % 10 == 0:
                    self.ts.save_checkpoint(checkpoint)
                    logger.info(f"Progress: {i + 1}/{len(symbols)} stocks processed")
                
            except Exception as e:
                logger.error(f"Failed to download {symbol}: {e}")
                checkpoint["failed"].append(symbol)
                fail_count += 1
        
        # Final checkpoint save
        checkpoint["end_time"] = datetime.now().isoformat()
        self.ts.save_checkpoint(checkpoint)
        
        # Clear checkpoint if all successful
        if fail_count == 0:
            self.ts.clear_checkpoint()
        
        summary = {
            "total": len(symbols),
            "success": success_count,
            "failed": fail_count,
            "skipped": len(completed) - success_count
        }
        
        logger.info(f"Download complete: {summary}")
        return summary
    
    def download_money_flow(self, trade_date: Optional[str] = None) -> dict:
        """
        Download money flow data for a trading day.
        
        Args:
            trade_date: Trading date 'YYYYMMDD'. Defaults to today.
        
        Returns:
            Summary dict.
        """
        if trade_date is None:
            trade_date = datetime.now().strftime("%Y%m%d")
        
        logger.info(f"Downloading money flow for {trade_date}")
        
        try:
            df = self.ts.get_money_flow(trade_date)
            
            if df.empty:
                return {"success": False, "message": "No data returned"}
            
            # Save to a dedicated file
            file_path = self.db.data_root / f"money_flow_{trade_date}.parquet"
            df.to_parquet(file_path, index=False)
            
            logger.info(f"Saved money flow data: {len(df)} stocks")
            return {"success": True, "count": len(df)}
            
        except Exception as e:
            logger.error(f"Failed to download money flow: {e}")
            return {"success": False, "error": str(e)}


def create_downloader(data_root: str = "./quant_data") -> DataDownloader:
    """
    Factory function to create a configured DataDownloader.
    
    Args:
        data_root: Root directory for data storage.
    
    Returns:
        Configured DataDownloader instance.
    """
    db_manager = DuckDBManager(data_root=data_root)
    ts_client = TushareClient(checkpoint_dir=data_root)
    validator = DataValidator(strict_mode=False)
    
    return DataDownloader(db_manager, ts_client, validator)
