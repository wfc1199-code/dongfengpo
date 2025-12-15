"""
自选股持久化存储模块 - 使用JSON文件
"""

import json
import os
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# 数据文件路径
DATA_DIR = Path(__file__).parent / "data"
FAVORITES_FILE = DATA_DIR / "favorites.json"

def ensure_data_dir():
    """确保数据目录存在"""
    DATA_DIR.mkdir(exist_ok=True)

def load_favorites() -> List[Dict]:
    """从文件加载自选股"""
    ensure_data_dir()

    if not FAVORITES_FILE.exists():
        # 如果文件不存在，创建默认数据
        default_favorites = [
            {"code": "000001", "name": "平安银行", "add_time": "2025-10-01T00:00:00"},
            {"code": "600000", "name": "浦发银行", "add_time": "2025-10-01T00:00:00"},
            {"code": "000002", "name": "万科A", "add_time": "2025-10-01T00:00:00"}
        ]
        save_favorites(default_favorites)
        return default_favorites

    try:
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
            favorites = json.load(f)
            logger.info(f"加载自选股: {len(favorites)}只")
            return favorites
    except Exception as e:
        logger.error(f"加载自选股失败: {e}")
        return []

def save_favorites(favorites: List[Dict]):
    """保存自选股到文件"""
    ensure_data_dir()

    try:
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, ensure_ascii=False, indent=2)
        logger.info(f"保存自选股: {len(favorites)}只")
    except Exception as e:
        logger.error(f"保存自选股失败: {e}")
        raise

def add_favorite(code: str, name: str) -> bool:
    """添加自选股"""
    from datetime import datetime

    favorites = load_favorites()

    # 检查是否已存在
    if any(f['code'] == code for f in favorites):
        logger.info(f"自选股已存在: {code}")
        return False

    # 添加新股票
    favorites.append({
        "code": code,
        "name": name,
        "add_time": datetime.now().isoformat()
    })

    save_favorites(favorites)
    logger.info(f"添加自选股: {code} {name}")
    return True

def remove_favorite(code: str) -> bool:
    """删除自选股"""
    favorites = load_favorites()

    # 查找并删除
    original_count = len(favorites)
    favorites = [f for f in favorites if f['code'] != code]

    if len(favorites) == original_count:
        logger.info(f"自选股不存在: {code}")
        return False

    save_favorites(favorites)
    logger.info(f"删除自选股: {code}")
    return True

def get_favorite_codes() -> List[str]:
    """获取所有自选股代码"""
    favorites = load_favorites()
    return [f['code'] for f in favorites]
