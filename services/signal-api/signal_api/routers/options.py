"""
期权搜索 API - 存根实现
由于期权服务未迁移到signal-api，这里提供一个空响应以防止前端404错误
"""
from fastapi import APIRouter, Query
from typing import Dict, List
import logging

router = APIRouter(
    prefix="/api/options",
    tags=["options"],
)

logger = logging.getLogger(__name__)


@router.get("/search")
async def search_options(
    q: str = Query("", description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50)
) -> Dict[str, object]:
    """
    期权搜索 - 存根实现
    
    返回空结果，防止前端因404而失败
    后续可以接入真实期权数据
    """
    logger.debug(f"期权搜索存根: q={q}, limit={limit}")
    return {
        "data": [],
        "total": 0,
        "message": "期权搜索暂不可用"
    }
