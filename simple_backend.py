#!/usr/bin/env python3
"""
简化的后端服务 - 仅提供前端需要的基本API
端口: 9001 (避免与Signal API的9000冲突)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="东风破简化后端")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/config/favorites")
async def get_favorites():
    """返回自选股列表"""
    return {
        "favorites": [
            {
                "code": "000001",
                "name": "平安银行",
                "current_price": 15.23,
                "change": 0.15,
                "change_percent": 0.99,
                "volume": 123456789,
                "amount": 1876543210,
                "turnover_rate": 0.52
            },
            {
                "code": "600000",
                "name": "浦发银行",
                "current_price": 8.76,
                "change": -0.03,
                "change_percent": -0.34,
                "volume": 98765432,
                "amount": 864197531,
                "turnover_rate": 0.41
            }
        ]
    }

@app.get("/api/kline/{symbol}")
async def get_kline(symbol: str, period: str = "day", limit: int = 100):
    """返回模拟K线数据"""
    # 返回简单的模拟数据
    return {
        "code": symbol,
        "data": [],
        "message": "请使用Signal API查看实时信号数据: http://localhost:9000/signals"
    }

if __name__ == "__main__":
    print("🚀 启动简化后端服务...")
    print("📍 端口: 9001")
    print("📊 Signal API: http://localhost:9000")
    print("🌐 前端请修改配置使用: http://localhost:9001")
    uvicorn.run(app, host="0.0.0.0", port=9001, log_level="info")
