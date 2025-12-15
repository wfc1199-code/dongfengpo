#!/bin/bash

# 东风破系统环境设置脚本
# 创建虚拟环境并安装依赖

echo "🔧 设置东风破系统Python环境..."

# 确保在正确的目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查Python
PYTHON_CMD=$(which python3)
echo "Python路径: $PYTHON_CMD"
$PYTHON_CMD --version

# 进入backend目录
cd backend

# 删除旧的虚拟环境（如果存在）
if [ -d "venv" ]; then
    echo "🗑️  删除旧的虚拟环境..."
    rm -rf venv
fi

# 创建新的虚拟环境
echo "📦 创建虚拟环境..."
$PYTHON_CMD -m venv venv

# 激活虚拟环境
echo "🔌 激活虚拟环境..."
source venv/bin/activate

# 更新pip
echo "⬆️  更新pip..."
python -m pip install --upgrade pip

# 安装依赖
echo "📥 安装Python依赖..."
python -m pip install -r requirements.txt

echo ""
echo "✅ 环境设置完成！"
echo ""
echo "🚀 现在可以启动系统："
echo "   ./start_dongfeng.sh"
echo ""
echo "💡 或者手动启动："
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python main.py"
