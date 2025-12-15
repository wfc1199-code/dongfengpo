#!/bin/bash

# 横盘突破监控工具 - 后端启动脚本

echo "=== 横盘突破监控工具 - macOS版 ==="
echo "正在启动后端服务..."

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

# 创建目录结构
mkdir -p backend/{api,core,models,utils}
mkdir -p data
mkdir -p frontend/src/{components,pages,utils}

# 进入后端目录
cd backend

# 检查依赖
if [ ! -f "requirements.txt" ]; then
    echo "错误: requirements.txt 不存在"
    exit 1
fi

# 安装依赖（如果需要）
echo "检查Python依赖..."
pip3 install -r requirements.txt

# 设置环境变量
export PYTHONPATH=$PYTHONPATH:$(pwd)

# 启动API服务
echo "启动API服务..."
echo "服务地址: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo "按 Ctrl+C 停止服务"
echo ""

python3 main.py 