#!/bin/bash

# 东风破系统 - 统一版本管理脚本
# 功能：备份、恢复、查看版本历史（调用Python统一版本管理器）

PROJECT_ROOT="/Users/wangfangchun/东风破"
BACKEND_DIR="$PROJECT_ROOT/backend"
CURRENT_VERSION_FILE="$PROJECT_ROOT/.current_version"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 创建必要目录
mkdir -p "$BACKUP_DIR"

# 获取当前版本号
get_current_version() {
    if [ -f "$CURRENT_VERSION_FILE" ]; then
        cat "$CURRENT_VERSION_FILE"
    else
        echo "v1.0.0"
    fi
}

# 生成新版本号
generate_version() {
    local current_version=$(get_current_version)
    local version_type=$1  # major, minor, patch
    
    # 解析版本号 v1.2.3
    local version=${current_version#v}
    IFS='.' read -r major minor patch <<< "$version"
    
    case $version_type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch|*)
            patch=$((patch + 1))
            ;;
    esac
    
    echo "v${major}.${minor}.${patch}"
}

# 创建版本备份（使用Python统一版本管理器）
create_backup() {
    echo -e "${BLUE}🔄 创建版本备份...${NC}"
    
    local version_type=${1:-patch}
    local message=${2:-"常规备份"}
    
    cd "$BACKEND_DIR"
    python3 -c "
import sys
sys.path.insert(0, '.')
from core.unified_version_manager import unified_version_manager

result = unified_version_manager.create_version(
    version_name='$message',
    version_type='$version_type',
    description='$message',
    tags=['manual', '$version_type']
)
print(f'✅ 版本: {result[\"version\"]}')
print(f'📦 备份: {result[\"backup_path\"]}')
print(f'📏 大小: {result[\"file_size\"]}')
"
    
    echo -e "${YELLOW}📌 新版本: $new_version${NC}"
    echo -e "${YELLOW}📝 备注: $message${NC}"
    
    # 创建备份目录
    mkdir -p "$backup_path"
    
    # 备份核心文件
    echo "📦 备份项目文件..."
    
    # 备份列表
    BACKUP_ITEMS=(
        "backend"
        "frontend/src"
        "frontend/package.json"
        "scripts"
        "config"
        "*.md"
        "*.json"
        "*.html"
    )
    
    # 执行备份
    for item in "${BACKUP_ITEMS[@]}"; do
        if [ -e "$PROJECT_ROOT/$item" ]; then
            cp -r "$PROJECT_ROOT/$item" "$backup_path/" 2>/dev/null
            echo "  ✓ $item"
        fi
    done
    
    # 创建备份信息文件
    cat > "$backup_path/backup_info.json" << EOF
{
    "version": "$new_version",
    "previous_version": "$(get_current_version)",
    "timestamp": "$timestamp",
    "date": "$(date '+%Y-%m-%d %H:%M:%S')",
    "message": "$message",
    "files_count": $(find "$backup_path" -type f | wc -l),
    "size": "$(du -sh "$backup_path" | cut -f1)",
    "git_commit": "$(cd $PROJECT_ROOT && git rev-parse HEAD 2>/dev/null || echo 'none')",
    "git_branch": "$(cd $PROJECT_ROOT && git branch --show-current 2>/dev/null || echo 'none')"
}
EOF
    
    # 压缩备份
    echo "🗜️  压缩备份文件..."
    cd "$BACKUP_DIR"
    tar -czf "${backup_name}.tar.gz" "$backup_name"
    rm -rf "$backup_name"
    
    # 更新版本记录
    update_version_db "$new_version" "$timestamp" "$message" "${backup_name}.tar.gz"
    
    # 更新当前版本
    echo "$new_version" > "$CURRENT_VERSION_FILE"
    
    echo -e "${GREEN}✅ 备份完成: ${backup_name}.tar.gz${NC}"
    echo -e "${GREEN}📍 位置: $BACKUP_DIR/${backup_name}.tar.gz${NC}"
    
    # 清理旧备份（保留最近10个）
    cleanup_old_backups
}

# 更新版本数据库
update_version_db() {
    local version=$1
    local timestamp=$2
    local message=$3
    local file=$4
    
    # 初始化或读取现有数据
    if [ ! -f "$VERSION_DB" ]; then
        echo '{"versions": []}' > "$VERSION_DB"
    fi
    
    # 使用Python更新JSON（更可靠）
    python3 << EOF
import json
import os

db_path = "$VERSION_DB"
with open(db_path, 'r') as f:
    data = json.load(f)

new_version = {
    "version": "$version",
    "timestamp": "$timestamp",
    "date": "$(date '+%Y-%m-%d %H:%M:%S')",
    "message": "$message",
    "file": "$file",
    "size": "$(du -sh $BACKUP_DIR/$file | cut -f1)"
}

data['versions'].append(new_version)

# 保留最近的版本在前
data['versions'] = sorted(data['versions'], key=lambda x: x['timestamp'], reverse=True)

with open(db_path, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
EOF
}

# 列出所有版本（使用Python统一版本管理器）
list_versions() {
    echo -e "${BLUE}📚 版本历史${NC}"
    echo "════════════════════════════════════════════════════════"
    
    cd "$BACKEND_DIR"
    python3 -c "
import sys
sys.path.insert(0, '.')
from core.unified_version_manager import unified_version_manager

versions = unified_version_manager.list_versions()
for v in versions:
    current = '✓' if v['is_current'] else ' '
    print(f\"{current} {v['semantic_version']:10} | {v['created_at'][:19]} | {v['file_size']:8} | {v['version_name']}\")
"
    
    python3 << EOF
import json
import os
from datetime import datetime

db_path = "$VERSION_DB"
if os.path.exists(db_path):
    with open(db_path, 'r') as f:
        data = json.load(f)
    
    current = "$(get_current_version)"
    
    for i, v in enumerate(data.get('versions', [])):
        is_current = "✓" if v['version'] == current else " "
        print(f"{is_current} {v['version']:10} | {v['date']} | {v['size']:8} | {v['message']}")
        
        if i < len(data['versions']) - 1:
            print("  │")
EOF
    
    echo "════════════════════════════════════════════════════════"
}

# 恢复到指定版本（使用Python统一版本管理器）
restore_version() {
    local target_version=$1
    
    if [ -z "$target_version" ]; then
        echo -e "${RED}❌ 请指定要恢复的版本号${NC}"
        list_versions
        return 1
    fi
    
    echo -e "${YELLOW}⚠️  准备恢复到版本: $target_version${NC}"
    read -p "确认恢复？(y/n): " confirm
    if [ "$confirm" != "y" ]; then
        echo "取消恢复"
        return
    fi
    
    cd "$BACKEND_DIR"
    python3 -c "
import sys
sys.path.insert(0, '.')
from core.unified_version_manager import unified_version_manager

try:
    result = unified_version_manager.restore_version('$target_version')
    print(f\"✅ {result['message']}\")
except Exception as e:
    print(f\"❌ 恢复失败: {e}\")
    sys.exit(1)
"
    
    echo -e "${YELLOW}⚠️  准备恢复到版本: $target_version${NC}"
    echo -e "${YELLOW}当前版本将被备份为: rollback_$(date +%Y%m%d_%H%M%S)${NC}"
    
    # 确认操作
    read -p "确认恢复？(y/n): " confirm
    if [ "$confirm" != "y" ]; then
        echo "取消恢复"
        return
    fi
    
    # 先备份当前版本
    create_backup patch "回退前自动备份"
    
    # 查找目标版本文件
    local backup_file=$(python3 << EOF
import json
db_path = "$VERSION_DB"
with open(db_path, 'r') as f:
    data = json.load(f)
for v in data.get('versions', []):
    if v['version'] == "$target_version":
        print(v['file'])
        break
EOF
)
    
    if [ -z "$backup_file" ]; then
        echo -e "${RED}❌ 未找到版本: $target_version${NC}"
        return 1
    fi
    
    local backup_path="$BACKUP_DIR/$backup_file"
    
    if [ ! -f "$backup_path" ]; then
        echo -e "${RED}❌ 备份文件不存在: $backup_path${NC}"
        return 1
    fi
    
    echo "🔄 开始恢复..."
    
    # 停止服务
    $PROJECT_ROOT/scripts/stop_dongfeng.sh
    
    # 解压备份
    cd "$BACKUP_DIR"
    tar -xzf "$backup_file"
    local extracted_dir="${backup_file%.tar.gz}"
    
    # 恢复文件
    echo "📝 恢复项目文件..."
    for item in backend frontend/src scripts config; do
        if [ -e "$extracted_dir/$item" ]; then
            rm -rf "$PROJECT_ROOT/$item"
            cp -r "$extracted_dir/$item" "$PROJECT_ROOT/$(dirname $item)/"
            echo "  ✓ $item"
        fi
    done
    
    # 恢复其他文件
    cp -f "$extracted_dir"/*.md "$PROJECT_ROOT/" 2>/dev/null
    cp -f "$extracted_dir"/*.json "$PROJECT_ROOT/" 2>/dev/null
    cp -f "$extracted_dir"/*.html "$PROJECT_ROOT/" 2>/dev/null
    
    # 清理
    rm -rf "$extracted_dir"
    
    # 更新版本号
    echo "$target_version" > "$CURRENT_VERSION_FILE"
    
    echo -e "${GREEN}✅ 已恢复到版本: $target_version${NC}"
    
    # 询问是否重启服务
    read -p "是否启动系统？(y/n): " restart
    if [ "$restart" = "y" ]; then
        $PROJECT_ROOT/scripts/start_dongfeng.sh
    fi
}

# 清理旧备份
cleanup_old_backups() {
    local keep_count=10
    local backup_count=$(ls -1 "$BACKUP_DIR"/*.tar.gz 2>/dev/null | wc -l)
    
    if [ $backup_count -gt $keep_count ]; then
        echo "🧹 清理旧备份（保留最近$keep_count个）..."
        ls -1t "$BACKUP_DIR"/*.tar.gz | tail -n +$((keep_count + 1)) | xargs rm -f
    fi
}

# 显示版本时间轴（使用Python统一版本管理器）
show_timeline() {
    echo -e "${BLUE}📈 版本时间轴${NC}"
    echo ""
    
    cd "$BACKEND_DIR"
    python3 -c "
import sys
sys.path.insert(0, '.')
from core.unified_version_manager import unified_version_manager

timeline = unified_version_manager.get_timeline(30)
for i, item in enumerate(timeline[:10]):
    marker = '●' if i == 0 else '○'
    color = '\\033[0;32m' if i == 0 else '\\033[0;34m'
    print(f\"{color}{marker} {item['version']}\\033[0m\")
    print(f\"  {item['date'][:19]}\")
    print(f\"  {item['name']}\")
    if i < len(timeline) - 1:
        print('  │')
"
    
    python3 << EOF
import json
import os
from datetime import datetime

db_path = "$VERSION_DB"
if os.path.exists(db_path):
    with open(db_path, 'r') as f:
        data = json.load(f)
    
    versions = data.get('versions', [])[:10]  # 显示最近10个
    
    for i, v in enumerate(versions):
        # 版本标记
        if i == 0:
            marker = "●"  # 最新版本
            color = "\033[0;32m"  # 绿色
        else:
            marker = "○"
            color = "\033[0;34m"  # 蓝色
        
        # 时间轴线条
        if i < len(versions) - 1:
            line = "│"
        else:
            line = " "
        
        print(f"{color}{marker} {v['version']}\033[0m")
        print(f"  {v['date']}")
        print(f"  {v['message']}")
        print(f"  大小: {v['size']}")
        if i < len(versions) - 1:
            print("  │")
EOF
}

# 主菜单
show_menu() {
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}     东风破 - 版本管理系统 v2.0        ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "当前版本: ${GREEN}$(get_current_version)${NC}"
    echo ""
    echo "1) 创建版本备份 (patch)"
    echo "2) 创建小版本备份 (minor)"
    echo "3) 创建大版本备份 (major)"
    echo "4) 查看版本列表"
    echo "5) 查看版本时间轴"
    echo "6) 恢复到指定版本"
    echo "7) 清理旧备份"
    echo "0) 退出"
    echo ""
}

# 交互式菜单
interactive_mode() {
    while true; do
        show_menu
        read -p "请选择操作: " choice
        
        case $choice in
            1)
                read -p "请输入备注信息: " message
                create_backup "patch" "$message"
                ;;
            2)
                read -p "请输入备注信息: " message
                create_backup "minor" "$message"
                ;;
            3)
                read -p "请输入备注信息: " message
                create_backup "major" "$message"
                ;;
            4)
                list_versions
                ;;
            5)
                show_timeline
                ;;
            6)
                list_versions
                echo ""
                read -p "请输入要恢复的版本号: " version
                restore_version "$version"
                ;;
            7)
                cleanup_old_backups
                echo -e "${GREEN}✅ 清理完成${NC}"
                ;;
            0)
                echo "退出版本管理系统"
                exit 0
                ;;
            *)
                echo -e "${RED}无效选项${NC}"
                ;;
        esac
        
        echo ""
        read -p "按回车继续..."
    done
}

# 命令行参数处理
case "$1" in
    backup|create)
        create_backup "${2:-patch}" "${3:-手动备份}"
        ;;
    list|ls)
        list_versions
        ;;
    timeline|tl)
        show_timeline
        ;;
    restore|rollback)
        restore_version "$2"
        ;;
    clean|cleanup)
        cleanup_old_backups
        ;;
    menu|interactive|"")
        interactive_mode
        ;;
    help|--help|-h)
        echo "用法: $0 [命令] [参数]"
        echo ""
        echo "命令:"
        echo "  backup [type] [message]  - 创建备份 (type: patch/minor/major)"
        echo "  list                     - 列出所有版本"
        echo "  timeline                 - 显示版本时间轴"
        echo "  restore <version>        - 恢复到指定版本"
        echo "  clean                    - 清理旧备份"
        echo "  menu                     - 交互式菜单"
        echo ""
        echo "示例:"
        echo "  $0 backup patch '修复bug'"
        echo "  $0 restore v1.0.0"
        ;;
    *)
        echo -e "${RED}未知命令: $1${NC}"
        echo "使用 $0 help 查看帮助"
        exit 1
        ;;
esac