#!/bin/bash

# 东风破系统停止脚本

echo "🛑 停止东风破系统..."

# 通过PID文件停止服务
if [ -f "logs/backend.pid" ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    echo "⏹️  停止后端服务 (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null || true
    rm -f logs/backend.pid
fi

if [ -f "logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    echo "⏹️  停止前端服务 (PID: $FRONTEND_PID)..."
    kill $FRONTEND_PID 2>/dev/null || true
    rm -f logs/frontend.pid
fi

# 强制清理端口占用
echo "🧹 清理端口占用..."
pkill -f "uvicorn.*main:app.*port.*9000" 2>/dev/null || true
pkill -f "react-scripts.*start" 2>/dev/null || true

echo "✅ 东风破系统已停止" 