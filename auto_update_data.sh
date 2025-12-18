#!/bin/bash
# 东风破 - 自动数据更新脚本
# 
# 用途: 每日盘后自动更新数据
# 时间: 每个交易日 17:00 (收盘后)
#
# 安装: crontab -e
# 添加: 0 17 * * 1-5 ~/东风破/auto_update_data.sh >> ~/东风破/logs/auto_update.log 2>&1

set -e  # 遇错即停

LOG_FILE=~/东风破/logs/auto_update_$(date +%Y%m%d).log
PROJECT_DIR=~/东风破/services/signal-api

echo "========================================"  | tee -a $LOG_FILE
echo "东风破 - 自动数据更新"                    | tee -a $LOG_FILE  
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"     | tee -a $LOG_FILE
echo "========================================"  | tee -a $LOG_FILE

cd $PROJECT_DIR

# 激活虚拟环境
source ../../venv/bin/activate

# 设置环境变量
export TUSHARE_TOKEN="cadca97e190afb9d92d6df92985d40affdfe34f9a6fcbde1e4abda30"

# 1. 增量更新（新股）
echo ""  | tee -a $LOG_FILE
echo "📥 步骤1: 增量更新新股数据..."  | tee -a $LOG_FILE
python scripts/update_daily_incremental.py 2>&1 | tee -a $LOG_FILE

# 2. 数据质量检查
echo ""  | tee -a $LOG_FILE
echo "🔍 步骤2: 数据质量检查..."  | tee -a $LOG_FILE
python scripts/inspect_data.py 2>&1 | tee -a $LOG_FILE

# 3. 清理90天前的旧数据
echo ""  | tee -a $LOG_FILE
echo "🧹 步骤3: 清理过期数据..."  | tee -a $LOG_FILE
python scripts/cleanup_old_data.py --keep-days 90 2>&1 | tee -a $LOG_FILE

echo ""  | tee -a $LOG_FILE
echo "✅ 自动更新完成!"  | tee -a $LOG_FILE
echo "========================================"  | tee -a $LOG_FILE

# 4. 发送通知（可选 - 需要配置通知工具）
# osascript -e 'display notification "数据更新完成" with title "东风破"'

exit 0
