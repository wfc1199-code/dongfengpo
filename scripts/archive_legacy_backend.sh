#!/bin/bash
# 东风破 - 备份 Legacy Backend v2.0.0
# 在删除前创建完整备份

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 生成备份目录名
BACKUP_DATE=$(date +%Y%m%d)
BACKUP_DIR="backups/backend-legacy-${BACKUP_DATE}"

echo "=========================================="
echo "  📦 备份 Legacy Backend v2.0.0"
echo "=========================================="
echo ""

# 检查 backend 目录是否存在
if [ ! -d "backend" ]; then
    echo -e "${RED}❌ backend 目录不存在${NC}"
    exit 1
fi

# 检查 main_modular.py 是否存在
if [ ! -f "backend/main_modular.py" ]; then
    echo -e "${RED}❌ backend/main_modular.py 不存在${NC}"
    exit 1
fi

# 创建备份目录
echo -e "${BLUE}📁 创建备份目录...${NC}"
mkdir -p "$BACKUP_DIR"
echo -e "${GREEN}✅ 备份目录: $BACKUP_DIR${NC}"
echo ""

# 备份文件
echo -e "${BLUE}📋 备份文件...${NC}"

# 备份 main_modular.py
if [ -f "backend/main_modular.py" ]; then
    cp "backend/main_modular.py" "$BACKUP_DIR/"
    echo -e "${GREEN}✅ 已备份: main_modular.py${NC}"
fi

# 备份 modules 目录
if [ -d "backend/modules" ]; then
    cp -r "backend/modules" "$BACKUP_DIR/"
    echo -e "${GREEN}✅ 已备份: modules/ 目录${NC}"
fi

# 备份 core 目录（如果存在且被使用）
if [ -d "backend/core" ]; then
    cp -r "backend/core" "$BACKUP_DIR/" 2>/dev/null || true
    echo -e "${GREEN}✅ 已备份: core/ 目录${NC}"
fi

echo ""

# 显示备份内容
echo -e "${BLUE}📊 备份内容:${NC}"
du -sh "$BACKUP_DIR"/*
echo ""

# 创建备份信息文件
cat > "$BACKUP_DIR/BACKUP_INFO.md" << EOF
# Legacy Backend v2.0.0 备份信息

**备份时间**: $(date '+%Y-%m-%d %H:%M:%S')
**备份原因**: 删除前备份，BMAD重构版本已稳定运行
**备份内容**:
- main_modular.py
- modules/ (7个业务模块)

**恢复方法**:
\`\`\`bash
# 恢复文件
cp backups/backend-legacy-${BACKUP_DATE}/main_modular.py backend/
cp -r backups/backend-legacy-${BACKUP_DATE}/modules backend/
\`\`\`

**注意事项**:
- 此备份为删除前安全备份
- 建议保留至少30天
- 确认BMAD版本稳定后再清理此备份
EOF

echo -e "${GREEN}✅ 备份信息文件已创建${NC}"
echo ""

# 显示备份摘要
echo "=========================================="
echo -e "${GREEN}✅ 备份完成！${NC}"
echo "=========================================="
echo ""
echo "备份位置: $BACKUP_DIR"
echo "备份大小: $(du -sh "$BACKUP_DIR" | cut -f1)"
echo ""
echo "下一步:"
echo "1. Git提交备份"
echo "2. 创建Git标签"
echo "3. 删除 backend 目录"
echo ""

