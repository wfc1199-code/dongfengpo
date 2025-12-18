#!/bin/bash

# 东风破 - 快速数据回填重启脚本 (并发优化版)
# 用法: ./restart_backfill_fast.sh

# 1. 停止旧进程 (如果存在)
ps -ef | grep backfill_all_market.py | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null
sleep 1

# 2. 进入项目服务目录
cd /Users/wangfangchun/东风破/services/signal-api || exit

# 3. 激活虚拟环境
source ../../venv/bin/activate

# 4. 设置 Tushare Token (必须)
export TUSHARE_TOKEN="cadca97e190afb9d92d6df92985d40affdfe34f9a6fcbde1e4abda30"

# 5. 启动并发优化版脚本
echo "=========================================="
echo "🚀 正在启动快速数据导入 (10线程并发)..."
echo "=========================================="
python scripts/backfill_all_market_fast.py
