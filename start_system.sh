#!/bin/bash

# 东风破系统启动脚本
# 一键启动所有服务

set -e

echo "=========================================="
echo "  东风破系统启动"
echo "=========================================="

# 检查Redis
echo ""
echo "📡 检查Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis未运行，请先启动Redis:"
    echo "   redis-server"
    exit 1
fi
echo "✅ Redis运行正常"

# 激活虚拟环境
echo ""
echo "🐍 激活Python虚拟环境..."
source venv/bin/activate

# 启动统一网关
echo ""
echo "🚀 启动统一API网关 (端口9000)..."
pkill -f "services/unified-gateway" 2>/dev/null || true
cd services/unified-gateway
python main.py > /tmp/gateway.log 2>&1 &
GATEWAY_PID=$!
cd ../..

# 等待网关启动
echo "⏳ 等待网关启动..."
sleep 3

# 检查网关
if curl -s http://localhost:9000/health > /dev/null; then
    echo "✅ 统一网关启动成功 (PID: $GATEWAY_PID)"
else
    echo "❌ 统一网关启动失败，请检查日志: tail -f /tmp/gateway.log"
    exit 1
fi

# 启动Signal API
echo ""
echo "🚀 启动Signal API微服务 (端口9001)..."
pkill -f "services/signal-api" 2>/dev/null || true
cd services/signal-api
python main.py > /tmp/signal-api.log 2>&1 &
SIGNAL_PID=$!
cd ../..

# 等待Signal API启动
sleep 2

# 检查Signal API
if curl -s http://localhost:9001/health > /dev/null; then
    echo "✅ Signal API启动成功 (PID: $SIGNAL_PID)"
else
    echo "⚠️  Signal API启动可能失败，请检查日志: tail -f /tmp/signal-api.log"
fi

# 显示状态
echo ""
echo "=========================================="
echo "  🎉 系统启动完成"
echo "=========================================="
echo ""
echo "📊 服务状态:"
echo "  - 统一网关:    http://localhost:9000"
echo "  - API文档:     http://localhost:9000/docs"
echo "  - Signal API:  http://localhost:9001"
echo "  - WebSocket:   ws://localhost:9000/ws"
echo ""
echo "🧪 测试命令:"
echo "  curl http://localhost:9000/health"
echo "  curl http://localhost:9000/api/stocks/000001/minute"
echo "  curl http://localhost:9000/signals?limit=10"
echo ""
echo "📝 日志位置:"
echo "  - 统一网关: /tmp/gateway.log"
echo "  - Signal API: /tmp/signal-api.log"
echo ""
echo "🛑 停止服务:"
echo "  pkill -f 'services/unified-gateway'"
echo "  pkill -f 'services/signal-api'"
echo ""
echo "📚 详细信息: cat MIGRATION_STATUS.md"
echo "=========================================="
