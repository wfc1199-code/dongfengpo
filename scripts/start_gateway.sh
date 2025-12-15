#!/bin/bash

# 东风破 API网关启动脚本
# 统一管理Legacy和新微服务的路由

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GATEWAY_DIR="$PROJECT_ROOT/services/api-gateway"

echo "🚀 启动东风破 API网关..."
echo "📂 项目路径: $PROJECT_ROOT"
echo "🌐 网关端口: 8080"

cd "$GATEWAY_DIR"

# 检查依赖
if ! python -c "import fastapi" 2>/dev/null; then
    echo "⚠️  缺少依赖,正在安装..."
    pip install -r requirements.txt
fi

# 检查端口占用
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  端口8080已被占用,尝试关闭..."
    lsof -ti:8080 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# 启动网关
echo "✅ 启动API网关..."
python main.py &
GATEWAY_PID=$!

echo "✅ API网关已启动 (PID: $GATEWAY_PID)"
echo "🔗 网关地址: http://localhost:8080"
echo "📊 健康检查: http://localhost:8080/gateway/health"
echo "📋 路由列表: http://localhost:8080/gateway/routes"
echo ""
echo "💡 提示: 使用 Ctrl+C 停止网关"

# 等待信号
wait $GATEWAY_PID
