#!/bin/bash

# 东风破项目 - 快速恢复到稳定版本脚本
# 版本: v1.0
# 用途: 当开发出现问题时，快速恢复到稳定运行状态

echo "🛟 东风破项目 - 快速恢复脚本"
echo "=============================="

# 停止当前运行的服务
echo "🛑 停止当前服务..."
./stop_dongfeng.sh 2>/dev/null || true
pkill -f "uvicorn.*main:app.*9000" 2>/dev/null || true
pkill -f "node.*react-scripts.*start" 2>/dev/null || true

# 检查Git状态
echo "📋 检查Git状态..."
if [ ! -d ".git" ]; then
    echo "❌ 错误: 当前目录不是Git仓库"
    exit 1
fi

# 显示当前状态
echo "📊 当前Git状态:"
git status --short
echo ""

# 询问恢复方式
echo "🔧 请选择恢复方式:"
echo "1) Git回退到稳定版本 (推荐)"
echo "2) 从物理备份恢复"
echo "3) 仅重启服务"
echo "4) 取消操作"
read -p "请选择 (1-4): " choice

case $choice in
    1)
        echo "🔄 回退到Git稳定版本..."
        # 保存当前工作（如果有未提交的更改）
        if [ -n "$(git status --porcelain)" ]; then
            echo "💾 保存当前工作到临时分支..."
            git add .
            git commit -m "临时保存 - $(date '+%Y-%m-%d %H:%M:%S')" || true
            git branch "temp-backup-$(date +%Y%m%d_%H%M%S)" || true
        fi
        
        # 回退到稳定版本
        git checkout stable-v1.0
        echo "✅ 已回退到稳定版本 stable-v1.0"
        ;;
    2)
        echo "📦 从物理备份恢复..."
        backup_dir=$(ls -t ../东风破_stable_backup_* 2>/dev/null | head -1)
        if [ -n "$backup_dir" ]; then
            echo "🔍 找到备份: $backup_dir"
            read -p "⚠️  这将覆盖当前所有文件，确认吗? (y/N): " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                cd ..
                rm -rf "东风破"
                cp -r "$backup_dir" "东风破"
                cd "东风破"
                echo "✅ 从物理备份恢复完成"
            else
                echo "❌ 用户取消操作"
                exit 1
            fi
        else
            echo "❌ 未找到物理备份文件"
            exit 1
        fi
        ;;
    3)
        echo "🔄 重启服务..."
        ;;
    4)
        echo "❌ 用户取消操作"
        exit 0
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

# 检查依赖
echo "🔧 检查Python依赖..."
cd backend
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "📦 安装Python依赖..."
    pip3 install -r requirements.txt
fi
cd ..

# 启动服务
echo "🚀 启动东风破系统..."
./start_dongfeng.sh

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 验证服务状态
echo "🔍 验证服务状态..."
frontend_status="❌"
backend_status="❌"

if curl -s http://localhost:3000 >/dev/null 2>&1; then
    frontend_status="✅"
fi

if curl -s http://localhost:9000 >/dev/null 2>&1; then
    backend_status="✅"
fi

echo ""
echo "📊 恢复结果:"
echo "  前端服务 (3000): $frontend_status"
echo "  后端服务 (9000): $backend_status"
echo ""

if [ "$frontend_status" = "✅" ] && [ "$backend_status" = "✅" ]; then
    echo "🎉 恢复成功！系统正常运行"
    echo "🌐 前端访问: http://localhost:3000"
    echo "🔗 后端API: http://localhost:9000"
    echo "📖 API文档: http://localhost:9000/docs"
else
    echo "⚠️  部分服务未正常启动，请检查日志:"
    echo "  后端日志: tail -f logs/backend.log"
    echo "  前端日志: tail -f logs/frontend.log"
fi

echo ""
echo "✨ 恢复操作完成！" 