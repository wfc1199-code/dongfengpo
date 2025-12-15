"""FastAPI application factory."""
from __future__ import annotations
from fastapi import FastAPI
from fastapi.responses import Response
from .routers import opportunities, signals, stocks
# Pipeline client imports (optional)
try:
    from .data.pipeline_client import close_pipeline_client, get_pipeline_client
except ImportError:
    # Fallback if pipeline_client doesn't exist
    async def get_pipeline_client():
        return None
    async def close_pipeline_client():
        pass
try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    def generate_latest():  # type: ignore[no-redef]
        return b""
def create_app(lifespan=None) -> FastAPI:
    """Create FastAPI app with optional lifespan."""
    app = FastAPI(
        title="Opportunity Signal API", 
        version="1.0.0",
        lifespan=lifespan
    )
    # Add CORS middleware to handle preflight requests
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}
    @app.get("/metrics")
    async def metrics() -> Response:
        """Prometheus metrics endpoint."""
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    app.include_router(opportunities.router)
    app.include_router(signals.router)
    app.include_router(stocks.router)
    
    # 尝试导入可选的路由模块
    try:
        from .routers import anomaly
        app.include_router(anomaly.router)
    except ImportError:
        pass
    
    try:
        from .routers import limit_up
        app.include_router(limit_up.router)
    except ImportError:
        pass
    
    try:
        from .routers import transactions
        app.include_router(transactions.router)
    except ImportError:
        pass
    
    try:
        from .routers import support_resistance
        app.include_router(support_resistance.router)
    except ImportError:
        pass
    
    try:
        from .routers import config
        app.include_router(config.router)
    except ImportError:
        pass
    
    try:
        from .routers import options
        app.include_router(options.router)
    except ImportError:
        pass

    return app
# Module-level app instance for uvicorn
app = create_app()
