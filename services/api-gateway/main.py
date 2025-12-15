#!/usr/bin/env python3
"""
东风破 - API网关服务
统一管理微服务的路由、认证、限流
"""
from fastapi import FastAPI, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import asyncio
from urllib.parse import urlparse
import fnmatch
try:
    from prometheus_client import Counter, Histogram, generate_latest
except ModuleNotFoundError:  # pragma: no cover
    # Allow running the gateway in minimal environments without prometheus_client installed.
    # Metrics endpoints will still respond, but collectors are stubbed.
    class _DummyMetric:  # noqa: D401
        def labels(self, **kwargs):  # type: ignore[no-untyped-def]
            return self
        def inc(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return None
        def observe(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return None
    Counter = lambda *a, **k: _DummyMetric()  # type: ignore[assignment]
    Histogram = lambda *a, **k: _DummyMetric()  # type: ignore[assignment]
    def generate_latest():  # type: ignore[no-redef]
        return b""
import time
# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# ---- structured logs (trace_id correlation) ----
def log_event(level: int, event: str, **fields: object) -> None:
    payload: Dict[str, object] = {
        "event": event,
        "service": "api-gateway",
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    payload.update({k: v for k, v in fields.items() if v is not None})
    logger.log(level, json.dumps(payload, ensure_ascii=False))
# Environment overrides (dev/test)
def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)
# 创建FastAPI应用
app = FastAPI(
    title="东风破 API Gateway",
    description="统一API网关 - 路由微服务",
    version="2.0.0"
)
# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Prometheus监控（使用条件注册避免重复）
try:
    REQUEST_COUNT = Counter('gateway_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
    REQUEST_LATENCY = Histogram('gateway_request_latency_seconds', 'Request latency', ['endpoint'])
except ValueError:
    # 如果已注册，从registry获取
    from prometheus_client import REGISTRY
    REQUEST_COUNT = REGISTRY._names_to_collectors.get('gateway_requests_total')
    REQUEST_LATENCY = REGISTRY._names_to_collectors.get('gateway_request_latency_seconds')
# 服务配置
SERVICES = {

    # 新微服务
    "signal-api": {
        # NOTE: signal-api code currently runs on 9001 in this repo; docker-compose maps 8000.
        # Use env override to make local verification & CI easier.
        "base_url": _env("DFP_SIGNAL_API_BASE_URL", "http://localhost:9001"),
        "timeout": 30.0,  # Increased from 15.0 to handle slow EastMoney API calls
        "routes": [
            # NOTE: wildcard routes do NOT match the non-trailing-slash path
            # e.g. "/api/v2/opportunities/*" won't match "/api/v2/opportunities"
            "/api/v2/opportunities",
            "/api/v2/signals/*",
            "/api/v2/signals",
            "/api/v2/opportunities/*",
            "/api/v2/market-data/*",  # Pipeline market data endpoints
            "/api/stocks/search",
            "/api/stocks/*/realtime",
            "/api/stocks/*/kline",
            "/api/stocks/*/minute",
            "/api/stocks/*/timeshare",
            "/api/stocks/*/behavior/analysis",
            "/api/anomaly/detect",
            "/api/anomaly/state/*",
            "/api/anomaly/peak-breakout/scan",
            "/api/anomaly/consolidation-breakout/scan",
            "/api/anomaly/time-segments",
            "/api/anomaly/time-segments/*",
            "/api/anomaly/hot-sectors",
            "/api/anomaly/sector-stocks/*",
            "/api/stocks/*/transactions",
            "/api/limit-up/predictions",
            "/api/limit-up/realtime-predictions",
            "/api/limit-up/second-board-candidates",
            "/api/transactions/*/details",
            "/api/support-resistance/tdx/calculate",
            "/api/support-resistance/*",  # GET /api/support-resistance/{stockCode} - must be single segment
            "/opportunities",  # 添加直接路径
            "/api/market-scanner/hot-sectors",
            "/api/market-scanner/sector-stocks/*",
            "/api/market-scanner/limit-up",
            "/api/market-scanner/second-board-candidates",
            "/api/config/favorites",
            "/api/config/favorites/*",
            "/api/config",
            "/api/config/system/monitoring-stocks",  # 监控股票列表
            "/api/system/monitoring-stocks",  # 兼容路径（需要重写）
            "/api/anomaly/market-anomaly/scan",  # 市场异动扫描（router prefix是/api/anomaly）
            "/api/market-anomaly/scan",  # 兼容路径
            "/api/options/search",
            "/health"  # 健康检查
        ]
    },
    "signal-streamer": {
        "base_url": _env("DFP_SIGNAL_STREAMER_BASE_URL", "http://localhost:8100"),
        "timeout": 30.0,  # WebSocket长连接
        "routes": [
            "/api/v2/ws/*"
        ]
    },
    "strategy-engine": {
        "base_url": _env("DFP_STRATEGY_ENGINE_BASE_URL", "http://localhost:8003"),
        "timeout": 10.0,
        "routes": [
            "/api/v2/strategies/*"
        ]
    },
    "backtest-service": {
        "base_url": _env("DFP_BACKTEST_SERVICE_BASE_URL", "http://localhost:8200"),  # 实际运行在8200
        "timeout": 60.0,  # 回测可能较慢
        "routes": [
            "/api/v2/backtest/*",
            "/backtests",  # 添加直接路径
            "/health"  # 健康检查（会与signal-api冲突，但可以通过路由优先级解决）
        ]
    }
}
# HTTP客户端池
http_clients: Dict[str, httpx.AsyncClient] = {}
@app.on_event("startup")
async def startup_event():
    """启动时创建HTTP客户端"""
    for service_name, config in SERVICES.items():
        http_clients[service_name] = httpx.AsyncClient(
            base_url=config["base_url"],
            timeout=config["timeout"],
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
    logger.info("API Gateway started, all clients initialized")
@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理客户端"""
    for client in http_clients.values():
        await client.aclose()
    logger.info("API Gateway shutdown complete")
def match_route(path: str, routes: List[str]) -> bool:
    """Match path against a list of route patterns.
    Supported:
    - exact: /api/v2/opportunities
    - wildcard anywhere: /api/stocks/*/realtime
    """
    for route in routes:
        if "*" in route:
            if fnmatch.fnmatch(path, route):
                return True
        else:
            if path == route:
                return True
    return False

def find_target_service(path: str) -> Optional[str]:
    """根据路径找到目标服务"""
    best_service: Optional[str] = None
    best_score: tuple[int, int, int] | None = None
    # Check signal-api first (higher priority for migrated routes)
    for service_name in ["signal-api", "signal-streamer", "opportunity-aggregator", "risk-guard"]:
        if service_name not in SERVICES:
            continue
        config = SERVICES[service_name]
        for route in config["routes"]:
            matched = False
            if "*" in route:
                # Special handling: signal-api's /api/support-resistance/* should only match single segment
                # (not sub-paths like /api/support-resistance/sh600000/analysis)
                if service_name == "signal-api" and route == "/api/support-resistance/*":
                    # Match only if path is exactly /api/support-resistance/{single_segment}
                    parts = path.split("/")
                    if len(parts) == 4 and parts[0] == "" and parts[1] == "api" and parts[2] == "support-resistance":
                        matched = True
                    else:
                        matched = False
                else:
                    matched = fnmatch.fnmatch(path, route)
            else:
                matched = path == route
            if not matched:
                continue
            wildcards = route.count("*")
            non_wildcard_len = len(route.replace("*", ""))
            is_exact = 1 if wildcards == 0 else 0
            score = (is_exact, -wildcards, non_wildcard_len)
            if best_score is None or score > best_score:
                best_score = score
                best_service = service_name
    return best_service
def rewrite_upstream_path(target_service: str, path: str) -> str:
    """
    Rewrite gateway-facing paths into upstream service paths.
    This is intentionally small and unit-testable to prevent regressions where
    the gateway forwards v2 paths but upstream services don't expose that prefix.
    """
    if target_service == "signal-api":
        # v2 -> internal (signal-api routers currently mount without "/api/v2" prefix)
        if path == "/api/v2/opportunities":
            return "/opportunities"
        if path.startswith("/api/v2/opportunities/"):
            return "/opportunities/" + path[len("/api/v2/opportunities/"):]
        if path == "/api/v2/signals":
            return "/signals"
        if path.startswith("/api/v2/signals/"):
            return "/signals/" + path[len("/api/v2/signals/"):]
        
        # Market data endpoints: /api/v2/market-data/* -> /api/stocks/*/timeshare or /api/stocks/*/minute
        # Format stock code: 000001 -> sz000001, 600000 -> sh600000
        def format_stock_symbol(stock_code: str) -> str:
            stock_code = stock_code.strip()
            if stock_code.startswith(("sh", "sz", "hk")):
                return stock_code
            # Shanghai: starts with 6
            if stock_code.startswith("6"):
                return "sh" + stock_code
            # default Shenzhen (0/2/3/...)
            return "sz" + stock_code
        
        if path.startswith("/api/v2/market-data/timeshare/"):
            symbol = path[len("/api/v2/market-data/timeshare/"):]
            formatted_symbol = format_stock_symbol(symbol)
            return f"/api/stocks/{formatted_symbol}/timeshare"
        if path.startswith("/api/v2/market-data/minute/"):
            symbol = path[len("/api/v2/market-data/minute/"):]
            formatted_symbol = format_stock_symbol(symbol)
            return f"/api/stocks/{formatted_symbol}/minute"
        # Market Scanner compatibility mappings
        if path.startswith("/api/market-scanner/hot-sectors"):
            return "/api/anomaly/hot-sectors"
        if path.startswith("/api/market-scanner/sector-stocks/"):
            return "/api/anomaly/sector-stocks/" + path[len("/api/market-scanner/sector-stocks/"):]
        if path.startswith("/api/market-scanner/limit-up"):
            return "/api/limit-up/predictions"
        if path.startswith("/api/market-scanner/second-board-candidates"):
            return "/api/limit-up/second-board-candidates"
        # Market anomaly scan compatibility
        if path == "/api/market-anomaly/scan":
            return "/api/anomaly/market-anomaly/scan"
        # System monitoring stocks compatibility
        if path == "/api/system/monitoring-stocks":
            return "/api/config/system/monitoring-stocks"
    return path
def _extract_trace_id(headers: Dict[str, str]) -> Optional[str]:
    """
    Extract trace id from request headers.
    Preference:
    - x-trace-id
    - traceparent (W3C, take trace-id part)
    """
    trace_id = headers.get("x-trace-id") or headers.get("X-Trace-Id")
    if trace_id:
        return trace_id
    traceparent = headers.get("traceparent") or headers.get("Traceparent")
    if traceparent:
        # format: version-traceid-spanid-flags
        parts = traceparent.split("-")
        if len(parts) >= 2 and len(parts[1]) >= 16:
            return parts[1]
    return None
def ensure_trace_id(headers: Dict[str, str]) -> str:
    """
    Ensure headers contain x-trace-id. Generate if missing.
    Returns the resolved trace_id.
    """
    trace_id = _extract_trace_id(headers)
    if not trace_id:
        trace_id = uuid.uuid4().hex
    headers["x-trace-id"] = trace_id
    return trace_id
def build_proxy_error_log(
    *,
    event: str,
    method: str,
    path: str,
    status: int,
    target_service: Optional[str],
    upstream_base_url: Optional[str],
    upstream_path: Optional[str],
    trace_id: Optional[str],
    detail: Optional[str] = None,
) -> Dict[str, object]:
    """Create a JSON-serializable structured error log."""
    payload: Dict[str, object] = {
        "event": event,
        "method": method,
        "path": path,
        "status": status,
        "target_service": target_service,
        "upstream_base_url": upstream_base_url,
        "upstream_path": upstream_path,
        "trace_id": trace_id,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if detail:
        payload["detail"] = detail
    return payload
def get_signal_streamer_opportunities_ws_url() -> str:
    """
    Resolve upstream WS URL for opportunities stream.
    Defaults to converting SERVICES['signal-streamer']['base_url'] to ws://... and
    appending /ws/opportunities, but can be overridden via env for port drift.
    """
    explicit = os.environ.get("DFP_SIGNAL_STREAMER_WS_URL")
    if explicit:
        return explicit
    base_url = SERVICES["signal-streamer"]["base_url"]
    parsed = urlparse(base_url)
    if parsed.scheme in ("ws", "wss"):
        # If already a ws URL, use as-is (assume includes correct path).
        return base_url
    scheme = "wss" if parsed.scheme == "https" else "ws"
    host = parsed.netloc or parsed.path  # tolerate base_url like "localhost:8100"
    return f"{scheme}://{host}/ws/opportunities"

@app.websocket("/ws")
async def ws_legacy(websocket: WebSocket) -> None:
    """
    Legacy WebSocket endpoint alias.
    Redirects to signal-streamer opportunities stream for compatibility.
    """
    await ws_opportunities(websocket)

@app.websocket("/ws/opportunities")
async def ws_opportunities(websocket: WebSocket) -> None:
    """
    Unified WS entrypoint. Proxies to signal-streamer /ws/opportunities.
    """
    # Resolve/ensure trace_id for the WS connection
    headers_in = {k: v for k, v in websocket.headers.items()}
    trace_id = ensure_trace_id(headers_in)
    await websocket.accept()
    upstream_url = get_signal_streamer_opportunities_ws_url()
    log_event(
        logging.INFO,
        "ws_proxy_connect",
        trace_id=trace_id,
        upstream_url=upstream_url,
        client=str(getattr(websocket, "client", None)),
        path="/ws/opportunities",
    )
    try:
        import websockets  # lazy import to avoid import cost in non-WS flows
        async with websockets.connect(
            upstream_url,
            ping_interval=None,
            extra_headers={"x-trace-id": trace_id},
        ) as upstream:
            async def _client_to_upstream() -> None:
                while True:
                    msg = await websocket.receive_text()
                    await upstream.send(msg)
            async def _upstream_to_client() -> None:
                async for msg in upstream:
                    await websocket.send_text(msg)
            done, pending = await asyncio.wait(
                [asyncio.create_task(_client_to_upstream()), asyncio.create_task(_upstream_to_client())],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            for task in done:
                task.result()
    except WebSocketDisconnect:
        log_event(
            logging.INFO,
            "ws_proxy_disconnect",
            trace_id=trace_id,
            upstream_url=upstream_url,
            path="/ws/opportunities",
        )
        return
    except Exception as e:  # noqa: BLE001
        log_event(
            logging.ERROR,
            "ws_proxy_error",
            trace_id=trace_id,
            upstream_url=upstream_url,
            error=str(e),
        )
        try:
            await websocket.close(code=1011)
        except Exception:  # noqa: BLE001
            return
@app.middleware("http")
async def gateway_middleware(request: Request, call_next):
    """网关中间件 - 路由转发"""
    start_time = time.time()
    path = request.url.path
    headers = dict(request.headers)
    trace_id = ensure_trace_id(headers)
    # 处理 CORS 预检请求
    # Handle CORS preflight (OPTIONS) requests directly - do NOT proxy them
    # The upstream services may not have CORS configured
    if request.method == "OPTIONS":
        return JSONResponse(
            content={},
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "86400",
            }
        )
    # 监控指标端点
    if path == "/metrics":
        return await call_next(request)
    # 健康检查端点和根路径
    if path in ("/", "/gateway/health", "/gateway/routes"):
        return await call_next(request)
    # Gateway直接实现的端点（不路由到其他服务）
    if path == "/api/system/status":
        return await call_next(request)
    # 找到目标服务
    target_service = find_target_service(path)
    if not target_service:
        log_event(logging.WARNING, "route_not_found", trace_id=trace_id, method=request.method, path=path)
        REQUEST_COUNT.labels(method=request.method, endpoint=path, status=404).inc()
        return JSONResponse(
            status_code=404,
            content={"error": "Service not found", "path": path, "trace_id": trace_id},
            headers={
                "x-trace-id": trace_id,
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true",
            },
        )
    try:
        # 获取客户端
        client = http_clients.get(target_service)
        if not client:
            raise HTTPException(status_code=503, detail=f"Service {target_service} unavailable")
        # 构建请求（含必要的路径重写）
        upstream_path = rewrite_upstream_path(target_service, path)
        url = upstream_path
        if request.url.query:
            url = f"{url}?{request.url.query}"
        headers.pop("host", None)  # 移除host头
        # 转发请求
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=await request.body()
        )
        # 记录监控
        latency = time.time() - start_time
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=path,
            status=response.status_code
        ).inc()
        REQUEST_LATENCY.labels(endpoint=path).observe(latency)
        log_event(
            logging.INFO,
            "proxy_request",
            trace_id=trace_id,
            method=request.method,
            path=path,
            target_service=target_service,
            upstream_path=upstream_path,
            status=response.status_code,
            latency_ms=round(latency * 1000, 2),
        )
        if response.status_code >= 400:
            log_event(
                logging.ERROR,
                "proxy_upstream_error",
                method=request.method,
                path=path,
                status=response.status_code,
                target_service=target_service,
                upstream_base_url=SERVICES.get(target_service, {}).get("base_url"),
                upstream_path=upstream_path,
                trace_id=trace_id,
            )
        # 返回响应
        response_headers = dict(response.headers)
        response_headers["x-trace-id"] = trace_id
        # 添加 CORS 头
        
        # Strip CORS headers from upstream to prevent duplicates, then add our own
        for cors_header in ["access-control-allow-origin", "access-control-allow-credentials", 
                           "access-control-allow-methods", "access-control-allow-headers"]:
            response_headers.pop(cors_header, None)
            # Also try title case
            response_headers.pop(cors_header.title().replace("-", "-"), None)
        
        # Add Gateway CORS headers
        response_headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
        response_headers["Access-Control-Allow-Credentials"] = "true"
        response_headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response_headers["Access-Control-Allow-Headers"] = "*"
        

        return JSONResponse(
            status_code=response.status_code,
            content=response.json() if response.headers.get("content-type", "").startswith("application/json") else {"data": response.text},
            headers=response_headers,
        )
    except httpx.TimeoutException:
        log_event(
            logging.ERROR,
            "proxy_timeout",
            trace_id=trace_id,
            method=request.method,
            path=path,
            status=504,
            target_service=target_service,
            upstream_base_url=SERVICES.get(target_service, {}).get("base_url") if target_service else None,
            upstream_path=rewrite_upstream_path(target_service, path) if target_service else None,
        )
        REQUEST_COUNT.labels(method=request.method, endpoint=path, status=504).inc()
        return JSONResponse(
            status_code=504,
            content={"error": "Gateway timeout", "service": target_service, "trace_id": trace_id},
            headers={
                "x-trace-id": trace_id,
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true",
            },
        )
    except Exception as e:
        log_event(
            logging.ERROR,
            "proxy_exception",
            trace_id=trace_id,
            method=request.method,
            path=path,
            status=500,
            target_service=target_service,
            upstream_base_url=SERVICES.get(target_service, {}).get("base_url") if target_service else None,
            upstream_path=rewrite_upstream_path(target_service, path) if target_service else None,
            detail=str(e),
        )
        REQUEST_COUNT.labels(method=request.method, endpoint=path, status=500).inc()
        return JSONResponse(
            status_code=500,
            content={"error": "Internal gateway error", "detail": str(e), "trace_id": trace_id},
            headers={"x-trace-id": trace_id},
        )
@app.get("/")
async def root() -> Dict[str, Any]:
    """API Gateway 根路径 - 显示服务信息"""
    return {
        "service": "东风破 API Gateway",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "health": "/gateway/health",
            "routes": "/gateway/routes",
            "metrics": "/metrics",
            "api_docs": "/docs",
        },
        "message": "请使用 /api/* 路径访问 API 端点",
    }
@app.get("/gateway/health")
async def health_check():
    """网关健康检查"""
    services_status = {}
    for service_name, config in SERVICES.items():
        try:
            client = http_clients.get(service_name)
            if client:
                response = await client.get("/health", timeout=2.0)
                services_status[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
            else:
                services_status[service_name] = {"status": "no_client"}
        except Exception as e:
            services_status[service_name] = {
                "status": "error",
                "error": str(e)
            }
    all_healthy = all(s["status"] == "healthy" for s in services_status.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "services": services_status
    }
@app.get("/gateway/routes")
async def list_routes():
    """列出所有路由规则"""
    routes = []
    for service_name, config in SERVICES.items():
        for route in config["routes"]:
            routes.append({
                "path": route,
                "service": service_name,
                "base_url": config["base_url"],
                "timeout": config["timeout"]
            })
    return {"routes": routes}


@app.get("/api/system/status")
async def get_system_status():
    """
    获取系统状态 - 兼容前端ManagementDashboard组件
    
    适配BMAD架构，返回各微服务健康状态
    """
    try:
        # 检查各服务健康状态
        services_status = {}
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 检查Signal API
            try:
                response = await client.get("http://localhost:9001/health")
                services_status["signal-api"] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time_ms": response.elapsed.total_seconds() * 1000 if hasattr(response, 'elapsed') else 0
                }
            except Exception as e:
                services_status["signal-api"] = {"status": "error", "error": str(e)}
            
            # 检查Signal Streamer
            try:
                response = await client.get("http://localhost:8100/health", timeout=2.0)
                services_status["signal-streamer"] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy"
                }
            except Exception as e:
                services_status["signal-streamer"] = {"status": "unhealthy", "error": str(e)}
            
            # 检查Strategy Engine
            try:
                response = await client.get("http://localhost:8003/health", timeout=2.0)
                services_status["strategy-engine"] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy"
                }
            except Exception as e:
                services_status["strategy-engine"] = {"status": "error", "error": str(e)}
        
        # 计算整体状态
        healthy_count = sum(1 for s in services_status.values() if s.get("status") == "healthy")
        total_count = len(services_status)
        overall_status = "running" if healthy_count == total_count else "degraded"
        
        return {
            "status": overall_status,
            "monitoring_stocks": 0,  # BMAD架构中由strategy-engine管理
            "connected_clients": 0,  # BMAD架构中由signal-streamer管理
            "anomaly_engine_initialized": services_status.get("strategy-engine", {}).get("status") == "healthy",
            "data_manager_initialized": services_status.get("signal-api", {}).get("status") == "healthy",
            "services": services_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
@app.get("/metrics")
async def metrics():
    """Prometheus监控指标"""
    return generate_latest()
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,  # 修改为标准网关端口
        reload=True,
        log_level="info"
    )