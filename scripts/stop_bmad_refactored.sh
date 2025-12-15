#!/bin/bash
# 东风破 - BMAD 重构架构停止脚本
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"
echo "=========================================="
echo "  🛑 停止 BMAD 重构架构服务"
echo "=========================================="
# 停止服务
if [ -f "logs/signal-api.pid" ]; then
    PID=$(cat logs/signal-api.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "停止 Signal API (PID: $PID)..."
        kill $PID 2>/dev/null || true
        rm logs/signal-api.pid
    fi
fi
if [ -f "logs/signal-streamer.pid" ]; then
    PID=$(cat logs/signal-streamer.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "停止 Signal Streamer (PID: $PID)..."
        kill $PID 2>/dev/null || true
        rm logs/signal-streamer.pid
    fi
fi
if [ -f "logs/opportunity-aggregator.pid" ]; then
    PID=$(cat logs/opportunity-aggregator.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "停止 Opportunity Aggregator (PID: $PID)..."
        kill $PID 2>/dev/null || true
        rm logs/opportunity-aggregator.pid
    fi
fi
if [ -f "logs/strategy-engine.pid" ]; then
    PID=$(cat logs/strategy-engine.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "停止 Strategy Engine (PID: $PID)..."
        kill $PID 2>/dev/null || true
        rm logs/strategy-engine.pid
    fi
fi
# 从PID文件中读取并停止服务
if [ -f "logs/legacy-backend.pid" ]; then
    LEGACY_PID=$(cat logs/legacy-backend.pid)
    if ps -p $LEGACY_PID > /dev/null 2>&1; then
        echo "停止 Legacy Backend (PID: $LEGACY_PID)..."
        kill $LEGACY_PID 2>/dev/null || true
        rm logs/legacy-backend.pid
    fi
fi
if [ -f "logs/api-gateway.pid" ]; then
    PID=$(cat logs/api-gateway.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "停止 API Gateway (PID: $PID)..."
        kill $PID 2>/dev/null || true
        rm logs/api-gateway.pid
    fi
fi
if [ -f "logs/frontend.pid" ]; then
    PID=$(cat logs/frontend.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "停止前端服务 (PID: $PID)..."
        kill $PID 2>/dev/null || true
        rm logs/frontend.pid
    fi
fi
# 清理端口
echo ""
echo "清理端口..."
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
lsof -ti:8002 | xargs kill -9 2>/dev/null || true
lsof -ti:8003 | xargs kill -9 2>/dev/null || true
lsof -ti:9000 | xargs kill -9 2>/dev/null || true
lsof -ti:9001 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
# 清理进程
pkill -f "signal_api.main" 2>/dev/null || true
pkill -f "api-gateway/main.py" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
echo ""
echo "✅ 所有服务已停止"
echo "=========================================="