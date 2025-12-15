# 东风破项目 - 安全开发指南

## 🛡️ 项目保护体系概述

为确保项目稳定开发，我们建立了完善的版本控制和备份体系，包括：
- ✅ Git版本控制
- ✅ 稳定版本标签
- ✅ 开发分支策略
- ✅ 物理备份机制
- ✅ 快速恢复脚本

## 📊 当前项目状态

### 稳定基线版本
- **版本**: stable-v1.0
- **Git标签**: `stable-v1.0`
- **创建时间**: 2025-01-28 06:30:00
- **状态**: ✅ 所有功能正常运行

### 分支结构
```
master          # 主分支（当前稳定版本）
├── stable-v1.0 # 稳定版本标签
└── development # 开发分支
```

## 🚀 安全开发流程

### 开始新开发
```bash
# 1. 确保在稳定版本
git checkout master
git status

# 2. 切换到开发分支
git checkout development

# 3. 创建功能分支（可选）
git checkout -b feature/新功能名称

# 4. 开始开发...
```

### 提交开发进度
```bash
# 经常性提交，保存开发进度
git add .
git commit -m "功能开发: 具体描述"

# 推送到开发分支
git push origin development
```

### 测试新功能
```bash
# 启动系统测试
./start_dongfeng.sh

# 访问测试
# 前端: http://localhost:3000
# 后端: http://localhost:9000
```

## 🛟 问题回退机制

### 方法1: 使用快速恢复脚本（推荐）
```bash
# 一键恢复到稳定版本
./restore_stable.sh

# 选择恢复方式:
# 1) Git回退到稳定版本 (推荐)
# 2) 从物理备份恢复  
# 3) 仅重启服务
# 4) 取消操作
```

### 方法2: 手动Git回退
```bash
# 保存当前工作
git add .
git commit -m "临时保存工作"

# 回退到稳定版本
git checkout stable-v1.0

# 重启服务
./start_dongfeng.sh
```

### 方法3: 物理备份恢复
```bash
# 查看可用备份
ls -la ../东风破_stable_backup_*

# 手动恢复（谨慎使用）
cd ..
cp -r 东风破_stable_backup_YYYYMMDD_HHMMSS 东风破_恢复
cd 东风破_恢复
./start_dongfeng.sh
```

## 📋 开发最佳实践

### 1. 频繁提交
```bash
# 每完成一个小功能就提交
git add .
git commit -m "明确的提交信息"
```

### 2. 功能分支开发
```bash
# 为每个大功能创建独立分支
git checkout -b feature/分时图优化
git checkout -b feature/新增预警系统
git checkout -b bugfix/修复异动检测
```

### 3. 测试验证
```bash
# 开发完成后必须测试
./start_dongfeng.sh

# 验证主要功能:
# - 前端页面正常加载
# - 后端API响应正常
# - 数据获取无错误
# - 分时图显示正常
```

### 4. 创建新的稳定版本
```bash
# 当开发完成且测试通过
git checkout master
git merge development
git tag -a stable-v1.1 -m "新稳定版本描述"

# 创建新的物理备份
cd ..
cp -r "东风破" "东风破_stable_backup_$(date +%Y%m%d_%H%M%S)"
cd "东风破"
```

## 🔧 服务管理

### 启动系统
```bash
./start_dongfeng.sh
```

### 停止系统
```bash
./stop_dongfeng.sh
```

### 查看服务状态
```bash
# 检查端口占用
lsof -i :3000,9000

# 检查进程
ps aux | grep -E "(uvicorn|node.*start)"

# 查看日志
tail -f logs/backend.log
tail -f logs/frontend.log
```

## 📁 重要文件说明

### 核心脚本
- `start_dongfeng.sh` - 启动系统
- `stop_dongfeng.sh` - 停止系统  
- `restore_stable.sh` - 快速恢复脚本

### 文档文件
- `PROJECT_STATUS.md` - 项目状态记录
- `DEVELOPMENT_GUIDE.md` - 开发指南（本文件）
- `PORT_CONFIG.md` - 端口配置说明

### 配置文件
- `.gitignore` - Git忽略文件配置
- `backend/requirements.txt` - Python依赖
- `frontend/package.json` - Node.js依赖

## ⚠️ 重要注意事项

### 开发前必读
1. **始终在开发分支进行新功能开发**
2. **频繁提交，避免工作丢失**
3. **测试通过后再合并到主分支**
4. **遇到问题立即回退到稳定版本**

### 紧急情况处理
```bash
# 如果系统完全无法启动
./restore_stable.sh

# 如果Git出现问题
cd ..
cp -r 东风破_stable_backup_* 东风破_恢复
cd 东风破_恢复

# 如果数据损坏
# 检查backup_*目录中的数据备份
```

### 备份策略
- **Git提交**: 每次开发都要提交
- **稳定标签**: 重要版本打标签
- **物理备份**: 定期创建完整备份
- **多重保障**: Git + 物理备份双重保护

## 🎯 开发目标建议

### 短期目标
- 在开发分支完成小功能
- 保持系统稳定运行
- 积累开发经验

### 中期目标  
- 完善核心功能
- 优化性能表现
- 增强用户体验

### 长期目标
- 建立完整的测试体系
- 实现自动化部署
- 扩展功能模块

## 📞 求助渠道

如果遇到无法解决的问题：
1. 查看本指南的回退方法
2. 检查 `PROJECT_STATUS.md` 的已知问题
3. 查看日志文件定位问题
4. 使用快速恢复脚本恢复系统

---

**记住：安全第一，稳定开发！** 🛡️ 