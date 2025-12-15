"""
配置管理 / 自选股 API
提供自选股的增删查接口，使用JSON文件存储
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

router = APIRouter(
    prefix="/api/config",
    tags=["config"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

# 配置文件路径
def _get_config_path() -> Path:
    # 先尝试相对于项目根目录
    paths = [
        Path.cwd() / "backend" / "data" / "config.json",
        Path(__file__).parent.parent.parent.parent.parent / "backend" / "data" / "config.json",
        Path.cwd() / "config.json",
    ]
    for p in paths:
        if p.exists():
            return p
    # 默认路径
    return Path.cwd() / "backend" / "data" / "config.json"


def _load_config() -> Dict[str, Any]:
    """加载配置文件"""
    config_path = _get_config_path()
    try:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
    return {"user_customization": {"自定义监控": {"自选股票池": []}}}


def _save_config(config: Dict[str, Any]) -> bool:
    """保存配置文件"""
    config_path = _get_config_path()
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存配置文件失败: {e}")
        return False


def _get_favorites_from_config(config: Dict[str, Any]) -> List[str]:
    """从配置中提取自选股代码列表"""
    raw_favorites = (
        config.get("user_customization", {})
        .get("自定义监控", {})
        .get("自选股票池", [])
    )
    codes = []
    for item in raw_favorites:
        if isinstance(item, dict):
            code = item.get("code", "")
        else:
            code = str(item)
        if code and code not in codes:
            codes.append(code)
    return codes


class FavoriteRequest(BaseModel):
    code: str
    name: Optional[str] = ""


@router.get("/favorites")
async def get_favorites():
    """获取自选股列表（包含实时数据）"""
    try:
        config = _load_config()
        codes = _get_favorites_from_config(config)
        
        if not codes:
            return {
                "favorites": [],
                "groups": [],
                "total": 0,
                "timestamp": datetime.now().isoformat()
            }
        
        # 获取实时数据
        favorite_details = []
        try:
            from ..data.data_sources import get_stock_data_manager
            data_manager = get_stock_data_manager()
            
            for code in codes[:50]:  # 限制50只避免超时
                try:
                    # 清理代码格式
                    clean_code = code.replace('sh', '').replace('sz', '').replace('hk', '')
                    realtime = await data_manager.get_realtime_quote(clean_code)
                    
                    if realtime:
                        favorite_details.append({
                            "code": code,
                            "name": realtime.get("name", ""),
                            "current_price": realtime.get("current_price", 0),
                            "change": realtime.get("change", 0),
                            "change_percent": realtime.get("change_percent", 0),
                            "volume": realtime.get("volume", 0),
                            "amount": realtime.get("amount", 0),
                            "high_price": realtime.get("high", 0),
                            "low_price": realtime.get("low", 0),
                            "open_price": realtime.get("open", 0),
                            "yesterday_close": realtime.get("yesterday_close", 0),
                        })
                    else:
                        favorite_details.append({"code": code, "name": ""})
                except Exception as e:
                    logger.warning(f"获取 {code} 实时数据失败: {e}")
                    favorite_details.append({"code": code, "name": ""})
                    
        except Exception as e:
            logger.warning(f"数据源不可用，返回基本信息: {e}")
            favorite_details = [{"code": code, "name": ""} for code in codes]
        
        return {
            "favorites": favorite_details,
            "groups": [],
            "total": len(favorite_details),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取自选股失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/favorites")
async def add_favorite(request: FavoriteRequest):
    """添加自选股"""
    try:
        config = _load_config()
        codes = _get_favorites_from_config(config)
        
        # 清理代码格式
        code = request.code.replace('sh', '').replace('sz', '').replace('hk', '')
        
        # 检查是否已存在
        if code in codes or request.code in codes:
            return {"success": False, "message": f"股票已在自选股中: {request.code}"}
        
        # 检查数量上限
        if len(codes) >= 200:
            return {"success": False, "message": "自选股数量已达上限(200)"}
        
        # 添加到配置
        if "user_customization" not in config:
            config["user_customization"] = {}
        if "自定义监控" not in config["user_customization"]:
            config["user_customization"]["自定义监控"] = {}
        if "自选股票池" not in config["user_customization"]["自定义监控"]:
            config["user_customization"]["自定义监控"]["自选股票池"] = []
        
        config["user_customization"]["自定义监控"]["自选股票池"].append({
            "code": request.code,
            "name": request.name or ""
        })
        
        if _save_config(config):
            logger.info(f"✅ 添加自选股: {request.code}")
            return {"success": True, "message": f"添加成功: {request.code}"}
        else:
            return {"success": False, "message": "保存配置失败"}
            
    except Exception as e:
        logger.error(f"添加自选股失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/favorites/{stock_code}")
async def remove_favorite(stock_code: str):
    """删除自选股"""
    try:
        config = _load_config()
        
        favorites_list = (
            config.get("user_customization", {})
            .get("自定义监控", {})
            .get("自选股票池", [])
        )
        
        # 查找并删除
        new_list = []
        found = False
        clean_code = stock_code.replace('sh', '').replace('sz', '').replace('hk', '')
        
        for item in favorites_list:
            if isinstance(item, dict):
                item_code = item.get("code", "")
            else:
                item_code = str(item)
            
            item_clean = item_code.replace('sh', '').replace('sz', '').replace('hk', '')
            
            if item_clean != clean_code and item_code != stock_code:
                new_list.append(item)
            else:
                found = True
        
        if not found:
            return {"success": False, "message": f"股票不在自选股中: {stock_code}"}
        
        config["user_customization"]["自定义监控"]["自选股票池"] = new_list
        
        if _save_config(config):
            logger.info(f"✅ 删除自选股: {stock_code}")
            return {"success": True, "message": f"删除成功: {stock_code}"}
        else:
            return {"success": False, "message": "保存配置失败"}
            
    except Exception as e:
        logger.error(f"删除自选股失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_config():
    """获取完整配置"""
    try:
        config = _load_config()
        return config
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/monitoring-stocks")
async def get_monitoring_stocks():
    """
    获取当前监控的股票列表 - 兼容前端ManagementDashboard组件
    
    适配BMAD架构，从配置和实时数据源获取
    """
    try:
        config = _load_config()
        codes = _get_favorites_from_config(config)
        
        # 获取用户自选股和热门板块股票
        user_stocks = []
        hot_sector_stocks = []
        
        if codes:
            # 获取实时数据
            try:
                from ..data.data_sources import get_stock_data_manager
                data_manager = get_stock_data_manager()
                
                # 用户自选股（前50只）
                for code in codes[:50]:
                    try:
                        clean_code = code.replace('sh', '').replace('sz', '').replace('hk', '')
                        realtime = await data_manager.get_realtime_quote(clean_code)
                        
                        if realtime:
                            user_stocks.append({
                                'code': code,
                                'name': realtime.get('name', ''),
                                'current_price': realtime.get('current_price', 0),
                                'change_percent': realtime.get('change_percent', 0),
                                'source': 'favorite'
                            })
                    except Exception as e:
                        logger.warning(f"获取 {code} 实时数据失败: {e}")
                        continue
            except Exception as e:
                logger.warning(f"数据源不可用: {e}")
        
        # 热门板块股票（从热门板块获取，限制30只）
        try:
            from ..routers.anomaly import fetch_eastmoney_sectors
            sectors = await fetch_eastmoney_sectors("concept", retry_count=2)
            
            # 取前30只热门板块股票
            for sector in sectors[:30]:
                code = sector.get('f12', '')
                if code and code not in codes:
                    hot_sector_stocks.append({
                        'code': code,
                        'name': sector.get('f14', ''),
                        'current_price': float(sector.get('f2', 0)),
                        'change_percent': float(sector.get('f3', 0)),
                        'source': 'hot_sector'
                    })
        except Exception as e:
            logger.warning(f"获取热门板块股票失败: {e}")
        
        return {
            "total_monitoring": len(codes) + len(hot_sector_stocks),
            "user_favorites_count": len(user_stocks),
            "hot_sector_stocks_count": len(hot_sector_stocks),
            "user_favorites": user_stocks,
            "hot_sector_stocks": hot_sector_stocks,
            "next_update_in_seconds": 900,  # 15分钟更新一次
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取监控股票列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取监控股票列表失败: {str(e)}")
