#!/bin/bash
# 东风破 - BMAD 重构后新架构启动脚本
# 启动事件驱动架构：API Gateway + Signal API + 数据管道
set -e
echo "=========================================="
echo "  🚀 东风破 BMAD 重构架构启动"
echo "=========================================="
# 确保在正确的目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"
# 检查 Redis
echo ""
echo "📡 检查 Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️  Redis未运行，正在启动..."
    redis-server > /dev/null 2>&1 &
    sleep 2
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis 已启动"
    else
        echo "❌ Redis 启动失败，请手动启动: redis-server"
        exit 1
    fi
else
    echo "✅ Redis 运行正常"
fi
# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先创建: python3 -m venv venv"
    exit 1
fi
# 激活虚拟环境
echo ""
echo "🐍 激活虚拟环境..."
source venv/bin/activate
# 清理可能冲突的端口
echo ""
echo "🛑 清理端口冲突..."
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
lsof -ti:9000 | xargs kill -9 2>/dev/null || true
lsof -ti:9001 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 2
# 创建日志目录
mkdir -p logs
# ============================================================
# Legacy Backend（已禁用 - 观察期）
# 如果重构版本稳定，可在1-2天后删除此段及backend目录
# 恢复方法：取消下方注释
# ============================================================
# echo ""
# echo "🚀 启动 Legacy Backend (端口 9000)..."
# cd backend
# nohup python main_modular.py > ../logs/legacy-backend.log 2>&1 &
# LEGACY_PID=$!
# cd ..
# echo "   PID: $LEGACY_PID"
# # 等待 Legacy Backend 启动
# echo "⏳ 等待 Legacy Backend 启动..."
# sleep 5
# # 验证 Legacy Backend
# for i in {1..10}; do
#     if curl -s http://localhost:9000/api/health > /dev/null 2>&1; then
#         echo "✅ Legacy Backend 响应正常"
#         break
#     else
#         echo "⏳ 等待 Legacy Backend 响应... ($i/10)"
#         sleep 2
#     fi
#     if [ $i -eq 10 ]; then
#         echo "❌ Legacy Backend 启动失败，请检查日志: logs/legacy-backend.log"
#         tail -20 logs/legacy-backend.log
#         exit 1
#     fi
# done
echo ""
echo "⚠️  Legacy Backend 已禁用（观察期）"
echo "   所有API已迁移到 Signal API (端口 9001)"
LEGACY_PID="disabled"

# 启动 Signal API (端口 9001)
echo ""
echo "🚀 启动 Signal API (端口 9001)..."
cd services/signal-api
nohup python main.py > ../../logs/signal-api.log 2>&1 &
SIGNAL_API_PID=$!
cd ../..
echo "   PID: $SIGNAL_API_PID"

# 启动 Signal Streamer (端口 8002) - 即使 Gateway 用 8100 转发，它实际要在 8002 听
echo ""
echo "🚀 启动 Signal Streamer (端口 8002)..."
cd services/signal-streamer
nohup python main.py > ../../logs/signal-streamer.log 2>&1 &
SIGNAL_STREAMER_PID=$!
cd ../..
echo "   PID: $SIGNAL_STREAMER_PID"

# 启动 Opportunity Aggregator (内部服务)
echo ""
echo "🚀 启动 Opportunity Aggregator..."
cd services/opportunity-aggregator
nohup python main.py > ../../logs/opportunity-aggregator.log 2>&1 &
AGGREGATOR_PID=$!
cd ../..
echo "   PID: $AGGREGATOR_PID"

# 启动 Strategy Engine (端口 8003)
echo ""
echo "🚀 启动 Strategy Engine (端口 8003)..."
cd services/strategy-engine
nohup python main.py > ../../logs/strategy-engine.log 2>&1 &
STRATEGY_PID=$!
cd ../..
echo "   PID: $STRATEGY_PID"

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 验证 Signal API
if curl -s http://localhost:9001/health > /dev/null 2>&1; then
    echo "✅ Signal API 响应正常"
else
    echo "⚠️  Signal API 可能还在启动中，请检查日志"
fi

# 验证 Signal Streamer (它是一个 WebSocket 服务，可能没有 /health，我们检查端口是否监听)
if lsof -i:8002 > /dev/null 2>&1; then
    echo "✅ Signal Streamer 端口正常监听"
else
    echo "❌ Signal Streamer 未启动 (端口 8002)"
fi

# 验证 Strategy Engine (它是一个纯后台服务，没有 HTTP 端口，检查进程)
if ps -p $STRATEGY_PID > /dev/null 2>&1; then
    echo "✅ Strategy Engine 进程运行中"
else
    echo "❌ Strategy Engine 未运行"
fi
# 启动 API Gateway (端口 8080)
echo ""
echo "🚀 启动 API Gateway (端口 8080)..."
cd services/api-gateway
# 关键：配置 Gateway 知道各个服务的真实端口
export DFP_SIGNAL_API_BASE_URL="http://localhost:9001"
export DFP_SIGNAL_STREAMER_BASE_URL="http://localhost:8002" 
export DFP_STRATEGY_ENGINE_BASE_URL="http://localhost:8003"
# 确保 Gateway 知道 Streamer 的 WebSocket 地址
# 注意：Gateway 里的 WS proxy 需要 ws:// 协议
export DFP_SIGNAL_STREAMER_WS_URL="ws://localhost:8002/ws/opportunities"

nohup python main.py > ../../logs/api-gateway.log 2>&1 &
GATEWAY_PID=$!
cd ../..
echo "   PID: $GATEWAY_PID"
# 等待 API Gateway 启动
echo "⏳ 等待 API Gateway 启动..."
sleep 5
# 验证 API Gateway
for i in {1..10}; do
    if curl -s http://localhost:8080/gateway/health > /dev/null 2>&1; then
        echo "✅ API Gateway 响应正常"
        break
    else
        echo "⏳ 等待 API Gateway 响应... ($i/10)"
        sleep 2
    fi
    if [ $i -eq 10 ]; then
        echo "❌ API Gateway 启动失败，请检查日志: logs/api-gateway.log"
        tail -20 logs/api-gateway.log
        exit 1
    fi
done
# 启动前端服务 (端口: 3000)
echo ""
echo "🎨 启动前端服务 (端口: 3000)..."
cd frontend
# 检查前端依赖
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm install
fi
# 配置前端使用 API Gateway
if [ ! -f ".env.local" ]; then
    echo "⚙️  配置前端环境变量..."
    cat > .env.local << 'EOF'
# BMAD 重构架构 - 使用 API Gateway
VITE_USE_API_GATEWAY=true
VITE_API_GATEWAY_URL=http://localhost:8080
VITE_PIPELINE_API_URL=http://localhost:8080/api/v2
# WebSocket 让前端连网关，网关会转发给 Streamer
VITE_PIPELINE_WS_URL=ws://localhost:8080/ws/opportunities
EOF
    echo "✅ 前端环境变量已配置"
fi
# 启动前端
nohup npm start > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   PID: $FRONTEND_PID"
# 返回项目根目录
cd ..
# 等待前端启动
echo "⏳ 等待前端服务启动..."
sleep 8
# 验证前端服务
for i in {1..5}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ 前端服务响应正常"
        break
    else
        echo "⏳ 等待前端响应... ($i/5)"
        sleep 3
    fi
    
    if [ $i -eq 5 ]; then
        echo "⚠️  前端服务可能还在启动中，请稍后访问 http://localhost:3000"
    fi
done
# 保存PID
echo $LEGACY_PID > logs/legacy-backend.pid
echo $SIGNAL_API_PID > logs/signal-api.pid
echo $SIGNAL_STREAMER_PID > logs/signal-streamer.pid
echo $AGGREGATOR_PID > logs/opportunity-aggregator.pid
echo $STRATEGY_PID > logs/strategy-engine.pid
echo $GATEWAY_PID > logs/api-gateway.pid
echo $FRONTEND_PID > logs/frontend.pid

# 显示服务状态
echo ""
echo "=========================================="
echo "  🎉 BMAD 重构架构启动完成"
echo "=========================================="
echo ""
echo "📊 服务地址:"
echo "  - 前端界面:    http://localhost:3000"
echo "  - API Gateway: http://localhost:8080"
echo "  - Signal API:  http://localhost:9001"
echo "  - Signal Streamer: http://localhost:8002"
echo "  - Strategy Engine: http://localhost:8003"
echo "  - Gateway 健康: http://localhost:8080/gateway/health"
echo "  - API 文档:     http://localhost:8080/docs (如果支持)"
echo ""
echo "🧪 测试命令:"
echo "  curl http://localhost:8080/gateway/health"
echo "  curl http://localhost:9001/health"
echo "  curl \"http://localhost:8080/api/stocks/search?keyword=000001\""
echo ""
echo "📝 日志位置:"
echo "  - 前端日志: logs/frontend.log"
echo "  - API Gateway: logs/api-gateway.log"
echo "  - Signal API: logs/signal-api.log"
echo "  - Streamer: logs/signal-streamer.log"
echo "  - Aggregator: logs/opportunity-aggregator.log"
echo "  - Strategy: logs/strategy-engine.log"
echo ""
echo "🛑 停止服务:"
echo "  ./scripts/stop_bmad_refactored.sh"
echo "  或手动: kill $LEGACY_PID $SIGNAL_API_PID $SIGNAL_STREAMER_PID $AGGREGATOR_PID $STRATEGY_PID $GATEWAY_PID $FRONTEND_PID"
echo ""
echo "📚 架构说明:"
echo "  - 事件驱动数据管道架构"
echo "  - API Gateway 统一入口"
echo "  - Signal API 提供 REST API"
echo "  - Redis Streams/PubSub 数据流"
echo ""
echo "=========================================="