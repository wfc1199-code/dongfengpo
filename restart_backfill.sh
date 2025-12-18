#!/bin/bash

# 东风破 - 数据回填重启脚本
# 用法: ./restart_backfill.sh

# 1. 进入项目服务目录
cd /Users/wangfangchun/东风破/services/signal-api || exit

# 2. 激活虚拟环境
source ../../venv/bin/activate

# 3. 设置 Tushare Token (必须)
export TUSHARE_TOKEN="cadca97e190afb9d92d6df92985d40affdfe34f9a6fcbde1e4abda30"

# 4. 启动脚本
echo "=========================================="
echo "🚀 正在重启数据导入任务 (断点续传模式)..."
echo "=========================================="
python scripts/backfill_all_market.py
