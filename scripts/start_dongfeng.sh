#!/bin/bash

# 东风破系统专用启动脚本
# 固定端口：前端3000，后端9000
# 避免与clean_quant_system(3600端口)混淆

echo "🌪️  启动东风破系统..."
echo "📍 项目端口配置："
echo "   - 前端: http://localhost:3000"
echo "   - 后端: http://localhost:9000"
echo "   - API文档: http://localhost:9000/docs"
echo ""

# 确保在正确的目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 停止可能冲突的服务
echo "🛑 清理端口冲突..."
pkill -f "uvicorn.*main:app.*9000" 2>/dev/null || true
pkill -f "react-scripts.*start.*3000" 2>/dev/null || true
lsof -ti:9000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

sleep 3

# 确保日志目录存在
mkdir -p logs

# 检查Python环境
echo "🔍 检查Python环境..."
PYTHON_CMD=$(which python3)
echo "Python路径: $PYTHON_CMD"
$PYTHON_CMD --version

# 创建和激活虚拟环境
echo "🔧 设置Python虚拟环境..."

# 检查虚拟环境是否存在（在项目根目录）
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    $PYTHON_CMD -m venv venv
fi

# 激活虚拟环境
echo "🔌 激活虚拟环境..."
source venv/bin/activate

# 更新pip
python -m pip install --upgrade pip

# 检查依赖
echo "🔍 检查Python依赖..."
cd backend
if ! python -c "import fastapi, uvicorn; print('✅ 依赖检查通过')" 2>/dev/null; then
    echo "❌ 缺少必要依赖，正在安装..."
    python -m pip install -r requirements.txt
fi

# 启动后端服务 (端口: 9000)
echo "🔧 启动后端服务 (端口: 9000)..."
nohup ../venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 9000 --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..
echo "✅ 后端服务启动 (PID: $BACKEND_PID)"

# 等待后端启动并验证
echo "⏳ 等待后端服务启动..."
sleep 8

# 验证后端是否正常运行
for i in {1..10}; do
    if curl -s http://localhost:9000/ > /dev/null 2>&1; then
        echo "✅ 后端服务响应正常"
        break
    else
        echo "⏳ 等待后端响应... ($i/10)"
        sleep 2
    fi
    
    if [ $i -eq 10 ]; then
        echo "❌ 后端启动失败，请检查日志: logs/backend.log"
        tail -10 logs/backend.log
        exit 1
    fi
done

# 启动前端服务 (端口: 3000)
echo "🎨 启动前端服务 (端口: 3000)..."
cd frontend

# 设置端口环境变量
export PORT=3000

nohup npm start > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ 前端服务启动 (PID: $FRONTEND_PID)"

# 返回项目根目录
cd ..

# 保存PID到文件，便于后续管理
echo $BACKEND_PID > logs/backend.pid
echo $FRONTEND_PID > logs/frontend.pid

echo ""
echo "🎉 东风破系统 v1.1 (优化版) 启动完成！"
echo "📊 访问地址："
echo "   - 前端界面: http://localhost:3000"
echo "   - API接口: http://localhost:9000"
echo "   - API文档: http://localhost:9000/docs"
echo ""
echo "📝 日志文件："
echo "   - 后端日志: logs/backend.log"
echo "   - 前端日志: logs/frontend.log"
echo ""
echo "⚠️  注意：东风破=3000端口，clean_quant_system=3600端口"
echo ""
echo "🔍 服务状态检查："
echo "   - 后端进程: PID $BACKEND_PID"
echo "   - 前端进程: PID $FRONTEND_PID" 