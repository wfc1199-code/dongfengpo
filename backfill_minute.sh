#!/bin/bash

# 东风破 - 分钟线数据回填脚本
# 用法: ./backfill_minute.sh [天数]
# 默认: 5天

DAYS=${1:-5}

cd /Users/wangfangchun/东风破/services/signal-api || exit
source ../../venv/bin/activate

export TUSHARE_TOKEN="cadca97e190afb9d92d6df92985d40affdfe34f9a6fcbde1e4abda30"

echo "=========================================="
echo "🚀 正在导入分钟线数据 (最近${DAYS}天)..."
echo "=========================================="

# 修改脚本中的DAYS参数
if [ "$DAYS" != "5" ]; then
    sed -i.bak "s/DAYS = 5/DAYS = $DAYS/" scripts/backfill_minute_data.py
fi

python scripts/backfill_minute_data.py

# 恢复默认值
if [ -f "scripts/backfill_minute_data.py.bak" ]; then
    mv scripts/backfill_minute_data.py.bak scripts/backfill_minute_data.py
fi
