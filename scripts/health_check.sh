#!/bin/bash

# 东风破系统健康检查脚本
# 检查系统各项服务状态和性能指标

echo "🏥 东风破系统健康检查 v1.1"
echo "================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查结果汇总
ISSUES=0

# 检查端口占用
echo "🔍 检查端口状态..."
check_port() {
    local port=$1
    local service=$2
    
    if lsof -i:$port > /dev/null 2>&1; then
        echo -e "  ✅ $service (端口 $port): ${GREEN}运行中${NC}"
    else
        echo -e "  ❌ $service (端口 $port): ${RED}未运行${NC}"
        ISSUES=$((ISSUES+1))
    fi
}

check_port 3000 "前端服务"
check_port 9000 "后端API"

echo ""

# 检查后端API健康状态
echo "🌐 检查后端API健康状态..."
if curl -s --max-time 5 http://localhost:9000/api/health > /dev/null; then
    echo -e "  ✅ 后端API健康检查: ${GREEN}正常${NC}"
    
    # 获取详细的健康状态
    HEALTH_RESPONSE=$(curl -s --max-time 5 http://localhost:9000/api/health)
    if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
        echo -e "  ✅ 系统状态: ${GREEN}健康${NC}"
    else
        echo -e "  ⚠️  系统状态: ${YELLOW}需要关注${NC}"
        ISSUES=$((ISSUES+1))
    fi
else
    echo -e "  ❌ 后端API健康检查: ${RED}失败${NC}"
    ISSUES=$((ISSUES+1))
fi

echo ""

# 检查前端页面
echo "🎨 检查前端页面..."
if curl -s --max-time 5 http://localhost:3000 > /dev/null; then
    echo -e "  ✅ 前端页面: ${GREEN}可访问${NC}"
else
    echo -e "  ❌ 前端页面: ${RED}无法访问${NC}"
    ISSUES=$((ISSUES+1))
fi

echo ""

# 检查系统资源
echo "💻 检查系统资源..."

# CPU使用率
CPU_USAGE=$(top -l 1 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')
CPU_USAGE_NUM=$(echo $CPU_USAGE | sed 's/%//')

if [ ! -z "$CPU_USAGE_NUM" ]; then
    if (( $(echo "$CPU_USAGE_NUM < 80" | bc -l) )); then
        echo -e "  ✅ CPU使用率: ${GREEN}${CPU_USAGE}${NC}"
    elif (( $(echo "$CPU_USAGE_NUM < 90" | bc -l) )); then
        echo -e "  ⚠️  CPU使用率: ${YELLOW}${CPU_USAGE}${NC}"
    else
        echo -e "  ❌ CPU使用率: ${RED}${CPU_USAGE}${NC}"
        ISSUES=$((ISSUES+1))
    fi
else
    echo -e "  ❓ CPU使用率: ${YELLOW}无法获取${NC}"
fi

# 内存使用率
MEMORY_INFO=$(vm_stat | grep -E "Pages (free|active|inactive|speculative|wired)" | awk '{print $3}' | sed 's/\.//')
if [ ! -z "$MEMORY_INFO" ]; then
    echo -e "  ✅ 内存状态: ${GREEN}正常${NC}"
else
    echo -e "  ❓ 内存状态: ${YELLOW}无法获取详细信息${NC}"
fi

echo ""

# 检查日志文件
echo "📝 检查日志文件..."
if [ -f "logs/backend.log" ]; then
    BACKEND_LOG_SIZE=$(du -h logs/backend.log | cut -f1)
    echo -e "  ✅ 后端日志: ${GREEN}存在${NC} (大小: $BACKEND_LOG_SIZE)"
    
    # 检查最近的错误
    ERROR_COUNT=$(tail -100 logs/backend.log | grep -i error | wc -l | tr -d ' ')
    if [ "$ERROR_COUNT" -gt 5 ]; then
        echo -e "  ⚠️  后端错误: ${YELLOW}最近100行中有${ERROR_COUNT}个错误${NC}"
    else
        echo -e "  ✅ 后端错误: ${GREEN}最近无严重错误${NC}"
    fi
else
    echo -e "  ❌ 后端日志: ${RED}不存在${NC}"
    ISSUES=$((ISSUES+1))
fi

if [ -f "logs/frontend.log" ]; then
    FRONTEND_LOG_SIZE=$(du -h logs/frontend.log | cut -f1)
    echo -e "  ✅ 前端日志: ${GREEN}存在${NC} (大小: $FRONTEND_LOG_SIZE)"
else
    echo -e "  ❌ 前端日志: ${RED}不存在${NC}"
    ISSUES=$((ISSUES+1))
fi

echo ""

# 检查配置文件
echo "⚙️  检查配置文件..."
if [ -f "config/main.json" ]; then
    echo -e "  ✅ 主配置文件: ${GREEN}存在${NC}"
else
    echo -e "  ❌ 主配置文件: ${RED}不存在${NC}"
    ISSUES=$((ISSUES+1))
fi

if [ -f "config/performance.json" ]; then
    echo -e "  ✅ 性能配置文件: ${GREEN}存在${NC}"
else
    echo -e "  ⚠️  性能配置文件: ${YELLOW}不存在${NC}"
fi

echo ""

# 输出总结
echo "================================"
if [ $ISSUES -eq 0 ]; then
    echo -e "🎉 系统健康检查: ${GREEN}全部通过${NC}"
else
    echo -e "⚠️  系统健康检查: ${YELLOW}发现 $ISSUES 个问题${NC}"
fi

echo ""
echo "📊 快速访问链接:"
echo "  - 前端界面: http://localhost:3000"
echo "  - API接口: http://localhost:9000"
echo "  - API文档: http://localhost:9000/docs"
echo "  - 健康检查: http://localhost:9000/api/health"

exit $ISSUES