#!/bin/bash

# 停止模块化单体服务

echo "🛑 停止东风破模块化单体系统..."

# 方式1：通过PID文件停止后端
if [ -f "logs/modular_backend.pid" ]; then
    PID=$(cat logs/modular_backend.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "✅ 已停止后端服务 (PID: $PID)"
        rm logs/modular_backend.pid
    else
        echo "⚠️  后端进程不存在: $PID"
        rm logs/modular_backend.pid
    fi
fi

# 方式1：通过PID文件停止前端
if [ -f "logs/frontend.pid" ]; then
    PID=$(cat logs/frontend.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "✅ 已停止前端服务 (PID: $PID)"
        rm logs/frontend.pid
    else
        echo "⚠️  前端进程不存在: $PID"
        rm logs/frontend.pid
    fi
fi

# 方式2：通过端口强制清理
lsof -ti:9000 | xargs kill -9 2>/dev/null && echo "✅ 已清理9000端口" || echo "⚠️  9000端口未占用"
lsof -ti:3000 | xargs kill -9 2>/dev/null && echo "✅ 已清理3000端口" || echo "⚠️  3000端口未占用"

echo "✅ 所有服务已停止"
