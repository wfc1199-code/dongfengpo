#!/bin/bash

# 东风破系统服务管理脚本
# 用于启动、停止、重启和检查所有微服务

set -e

PROJECT_ROOT="/Users/wangfangchun/东风破"
LOG_DIR="$PROJECT_ROOT/logs"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 服务列表 (服务名:目录:端口)
SERVICES=(
    "collector-gateway:services/collector-gateway:0"
    "data-cleaner:services/data-cleaner:0"
    "feature-pipeline:services/feature-pipeline:0"
    "strategy-engine:services/strategy-engine:0"
    "signal-api:services/signal-api:8000"
)

# 创建日志目录
mkdir -p "$LOG_DIR"

# 打印消息
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Redis是否运行
check_redis() {
    if redis-cli ping > /dev/null 2>&1; then
        log_success "Redis is running"
        return 0
    else
        log_error "Redis is not running. Please start Redis first: redis-server"
        return 1
    fi
}

# 检查服务是否运行
is_service_running() {
    local service_name=$1
    local pid_file="$LOG_DIR/${service_name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# 启动单个服务
start_service() {
    local service_name=$1
    local service_dir=$2
    local service_port=$3

    if is_service_running "$service_name"; then
        log_warning "$service_name is already running"
        return 0
    fi

    log_info "Starting $service_name..."

    cd "$PROJECT_ROOT/$service_dir"

    # 启动服务并将PID保存
    nohup python main.py > "$LOG_DIR/${service_name}.log" 2>&1 &
    local pid=$!
    echo $pid > "$LOG_DIR/${service_name}.pid"

    # 等待服务启动
    sleep 2

    if ps -p $pid > /dev/null 2>&1; then
        log_success "$service_name started (PID: $pid)"

        # 如果有端口,检查端口是否监听
        if [ "$service_port" != "0" ]; then
            sleep 1
            if lsof -i:$service_port > /dev/null 2>&1; then
                log_success "$service_name is listening on port $service_port"
            else
                log_warning "$service_name started but port $service_port is not ready yet"
            fi
        fi
        return 0
    else
        log_error "$service_name failed to start. Check logs: $LOG_DIR/${service_name}.log"
        return 1
    fi
}

# 停止单个服务
stop_service() {
    local service_name=$1
    local pid_file="$LOG_DIR/${service_name}.pid"

    if [ ! -f "$pid_file" ]; then
        log_warning "$service_name is not running (no PID file)"
        return 0
    fi

    local pid=$(cat "$pid_file")

    if ! ps -p "$pid" > /dev/null 2>&1; then
        log_warning "$service_name is not running (PID $pid does not exist)"
        rm -f "$pid_file"
        return 0
    fi

    log_info "Stopping $service_name (PID: $pid)..."
    kill $pid

    # 等待进程结束
    local count=0
    while ps -p $pid > /dev/null 2>&1; do
        sleep 1
        count=$((count + 1))
        if [ $count -gt 10 ]; then
            log_warning "Force killing $service_name..."
            kill -9 $pid
            break
        fi
    done

    rm -f "$pid_file"
    log_success "$service_name stopped"
}

# 查看服务状态
status_service() {
    local service_name=$1
    local service_port=$2
    local pid_file="$LOG_DIR/${service_name}.pid"

    printf "%-25s" "$service_name"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            printf "${GREEN}RUNNING${NC} (PID: $pid)"
            if [ "$service_port" != "0" ]; then
                if lsof -i:$service_port > /dev/null 2>&1; then
                    printf " [Port: $service_port ✓]"
                else
                    printf " [Port: $service_port ${RED}✗${NC}]"
                fi
            fi
            echo ""
            return 0
        else
            printf "${RED}STOPPED${NC} (stale PID: $pid)\n"
            return 1
        fi
    else
        printf "${RED}STOPPED${NC}\n"
        return 1
    fi
}

# 启动所有服务
start_all() {
    log_info "Starting all services..."

    if ! check_redis; then
        return 1
    fi

    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service_name service_dir service_port <<< "$service_config"
        start_service "$service_name" "$service_dir" "$service_port"
        sleep 1
    done

    log_success "All services started"
}

# 停止所有服务
stop_all() {
    log_info "Stopping all services..."

    # 反向停止服务
    for ((idx=${#SERVICES[@]}-1 ; idx>=0 ; idx--)); do
        IFS=':' read -r service_name service_dir service_port <<< "${SERVICES[idx]}"
        stop_service "$service_name"
    done

    log_success "All services stopped"
}

# 重启所有服务
restart_all() {
    log_info "Restarting all services..."
    stop_all
    sleep 2
    start_all
}

# 查看所有服务状态
status_all() {
    echo ""
    echo "===== 东风破系统服务状态 ====="
    echo ""

    # Redis状态
    printf "%-25s" "Redis"
    if redis-cli ping > /dev/null 2>&1; then
        printf "${GREEN}RUNNING${NC}\n"
    else
        printf "${RED}STOPPED${NC}\n"
    fi

    echo ""

    # 各服务状态
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service_name service_dir service_port <<< "$service_config"
        status_service "$service_name" "$service_port"
    done

    echo ""
    echo "===== Redis数据流状态 ====="
    echo ""

    # Redis Stream统计
    if redis-cli ping > /dev/null 2>&1; then
        printf "%-30s %s\n" "raw_ticks:" "$(redis-cli XLEN dfp:raw_ticks 2>/dev/null || echo 0) messages"
        printf "%-30s %s\n" "clean_ticks:" "$(redis-cli XLEN dfp:clean_ticks 2>/dev/null || echo 0) messages"
        printf "%-30s %s\n" "strategy_signals:" "$(redis-cli XLEN dfp:strategy_signals 2>/dev/null || echo 0) messages"
    else
        echo "Redis not available"
    fi

    echo ""
}

# 查看服务日志
logs() {
    local service_name=$1
    local lines=${2:-50}

    if [ -z "$service_name" ]; then
        log_error "Please specify a service name"
        echo "Available services:"
        for service_config in "${SERVICES[@]}"; do
            IFS=':' read -r svc_name _ _ <<< "$service_config"
            echo "  - $svc_name"
        done
        return 1
    fi

    local log_file="$LOG_DIR/${service_name}.log"

    if [ ! -f "$log_file" ]; then
        log_error "Log file not found: $log_file"
        return 1
    fi

    log_info "Showing last $lines lines of $service_name log:"
    echo ""
    tail -n "$lines" "$log_file"
}

# 清理旧日志
clean_logs() {
    log_info "Cleaning old logs..."
    rm -f "$LOG_DIR"/*.log
    rm -f "$LOG_DIR"/*.pid
    log_success "Logs cleaned"
}

# 显示帮助
show_help() {
    cat << EOF
东风破系统服务管理脚本

用法: $0 <command> [options]

命令:
  start           启动所有服务
  stop            停止所有服务
  restart         重启所有服务
  status          查看所有服务状态
  logs <service>  查看指定服务日志
  clean           清理旧日志文件

服务列表:
EOF
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service_name _ service_port <<< "$service_config"
        if [ "$service_port" != "0" ]; then
            echo "  - $service_name (Port: $service_port)"
        else
            echo "  - $service_name"
        fi
    done

    cat << EOF

示例:
  $0 start                     # 启动所有服务
  $0 stop                      # 停止所有服务
  $0 status                    # 查看状态
  $0 logs strategy-engine      # 查看策略引擎日志
  $0 logs signal-api 100       # 查看信号API最近100行日志

EOF
}

# 主程序
main() {
    local command=${1:-}

    case $command in
        start)
            start_all
            ;;
        stop)
            stop_all
            ;;
        restart)
            restart_all
            ;;
        status)
            status_all
            ;;
        logs)
            logs "$2" "$3"
            ;;
        clean)
            clean_logs
            ;;
        help|--help|-h|"")
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
