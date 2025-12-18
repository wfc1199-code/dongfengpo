"""
Backtest Engine - 回测和参数优化微服务

提供策略回测、性能分析、报告生成、参数优化等功能。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import backtest, optimize
from .config import settings

app = FastAPI(
    title="Backtest Engine API",
    description="量化策略回测与参数优化服务",
    version="1.0.0",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(optimize.router, prefix="/api/optimize", tags=["optimize"])


@app.get("/")
async def root():
    """健康检查"""
    return {
        "service": "Backtest Engine",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9003)
