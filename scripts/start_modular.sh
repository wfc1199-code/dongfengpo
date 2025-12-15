#!/bin/bash

# 东风破 - 模块化单体版启动脚本
# 启动新的模块化架构

set -e

echo "=========================================="
echo "  🏗️ 东风破模块化单体系统启动"
echo "=========================================="

# 确保在正确的目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 停止可能冲突的服务
echo ""
echo "🛑 清理端口冲突..."
lsof -ti:9000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 2

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先创建: python3 -m venv venv"
    exit 1
fi

# 激活虚拟环境
echo "🐍 激活虚拟环境..."
source venv/bin/activate

# 在受限环境下使用本地回环地址
export API_HOST=${API_HOST:-127.0.0.1}
export DEBUG=${DEBUG:-0}

# 启动后端（模块化版本）
echo ""
echo "🚀 启动模块化后端服务..."
cd backend
nohup ../venv/bin/python main_modular.py > ../logs/modular_backend.log 2>&1 &
BACKEND_PID=$!
cd ..

echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"

# 等待后端启动
echo "⏳ 等待后端启动..."
sleep 5

# 验证后端
for i in {1..10}; do
    if curl -s http://localhost:9000/health > /dev/null 2>&1; then
        echo "✅ 后端服务响应正常"
        break
    else
        echo "⏳ 等待后端响应... ($i/10)"
        sleep 2
    fi

    if [ $i -eq 10 ]; then
        echo "❌ 后端启动失败，请检查日志: logs/modular_backend.log"
        tail -20 logs/modular_backend.log
        exit 1
    fi
done

# 显示模块信息
echo ""
echo "📦 已加载的模块:"
curl -s http://localhost:9000/modules | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data['modules']:
    print(f\"  - {m['name']:15} {m['prefix']:25} [{', '.join(m['tags'])}]\")
" 2>/dev/null || echo "  (无法获取模块列表)"

# 启动前端服务 (端口: 3000)
echo ""
echo "🎨 启动前端服务 (端口: 3000)..."
cd frontend

# 检查前端依赖
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖..."
    npm install
fi

# 设置端口环境变量
export PORT=3000

nohup npm start > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ 前端服务启动 (PID: $FRONTEND_PID)"

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
        echo "⚠️ 前端服务可能还在启动中，请稍后访问 http://localhost:3000"
    fi
done

# 保存PID
echo $BACKEND_PID > logs/modular_backend.pid
echo $FRONTEND_PID > logs/frontend.pid

echo ""
echo "=========================================="
echo "  🎉 系统启动完成"
echo "=========================================="
echo ""
echo "📊 服务地址:"
echo "  - 前端界面:    http://localhost:3000"
echo "  - 后端API:     http://localhost:9000"
echo "  - API文档:     http://localhost:9000/docs"
echo "  - 模块列表:    http://localhost:9000/modules"
echo ""
echo "🧪 测试命令:"
echo "  curl http://localhost:9000/health"
echo "  curl http://localhost:9000/modules"
echo "  curl http://localhost:9000/api/limit-up/health"
echo ""
echo "📝 日志位置:"
echo "  - 前端日志: logs/frontend.log"
echo "  - 后端日志: logs/modular_backend.log"
echo "  - 详细日志: backend/logs/dongfeng_modular.log"
echo ""
echo "🛑 停止服务:"
echo "  ./scripts/stop_modular.sh"
echo "  或手动: kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "📚 架构文档: MODULAR_MONOLITH_GUIDE.md"
echo "=========================================="
