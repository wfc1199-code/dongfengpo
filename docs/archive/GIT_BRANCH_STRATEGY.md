# Git分支管理策略

## 🌳 分支结构

```
main (生产环境)
  ├── develop (开发主线)
  │     ├── feature/xxx (功能分支)
  │     ├── bugfix/xxx (Bug修复)
  │     └── refactor/xxx (重构分支)
  ├── release/v1.x.x (发布分支)
  └── hotfix/xxx (紧急修复)
```

## 📋 分支说明

### 1. 主分支 (main)
- **用途**: 生产环境代码
- **权限**: 保护分支，需要PR和审查
- **更新**: 只能从release或hotfix合并
- **标签**: 每次发布打tag

### 2. 开发分支 (develop)
- **用途**: 开发集成分支
- **权限**: 保护分支，需要PR
- **更新**: 从feature/bugfix合并
- **规则**: 始终保持可运行状态

### 3. 功能分支 (feature/*)
- **命名**: `feature/功能名称`
- **来源**: 从develop创建
- **目标**: 合并回develop
- **生命周期**: 功能完成后删除

### 4. 修复分支 (bugfix/*)
- **命名**: `bugfix/问题描述`
- **来源**: 从develop创建
- **目标**: 合并回develop
- **生命周期**: 修复完成后删除

### 5. 发布分支 (release/*)
- **命名**: `release/v1.2.0`
- **来源**: 从develop创建
- **目标**: 合并到main和develop
- **用途**: 发布前的最终测试

### 6. 热修复分支 (hotfix/*)
- **命名**: `hotfix/紧急问题`
- **来源**: 从main创建
- **目标**: 合并到main和develop
- **用途**: 生产环境紧急修复

## 🔄 工作流程

### 1. 开发新功能
```bash
# 1. 从develop创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/early-capture

# 2. 开发功能
git add .
git commit -m "feat: 实现早盘捕捉功能"

# 3. 推送分支
git push origin feature/early-capture

# 4. 创建PR到develop
# 在GitHub/GitLab上创建Pull Request

# 5. 代码审查通过后合并
# 删除功能分支
git branch -d feature/early-capture
```

### 2. 修复Bug
```bash
# 1. 从develop创建修复分支
git checkout develop
git checkout -b bugfix/data-delay

# 2. 修复问题
git add .
git commit -m "fix: 修复数据延迟问题"

# 3. 推送并创建PR
git push origin bugfix/data-delay
```

### 3. 发布版本
```bash
# 1. 从develop创建发布分支
git checkout develop
git checkout -b release/v1.2.0

# 2. 更新版本号
echo "v1.2.0" > VERSION
git commit -am "chore: bump version to v1.2.0"

# 3. 测试和修复
# ... 进行最终测试 ...

# 4. 合并到main
git checkout main
git merge --no-ff release/v1.2.0
git tag -a v1.2.0 -m "Release version 1.2.0"

# 5. 合并回develop
git checkout develop
git merge --no-ff release/v1.2.0

# 6. 删除发布分支
git branch -d release/v1.2.0
```

### 4. 紧急修复
```bash
# 1. 从main创建热修复分支
git checkout main
git checkout -b hotfix/critical-bug

# 2. 修复问题
git add .
git commit -m "hotfix: 修复关键bug"

# 3. 合并到main
git checkout main
git merge --no-ff hotfix/critical-bug
git tag -a v1.1.1 -m "Hotfix version 1.1.1"

# 4. 合并到develop
git checkout develop
git merge --no-ff hotfix/critical-bug

# 5. 删除分支
git branch -d hotfix/critical-bug
```

## 📝 提交规范

### 提交信息格式
```
<类型>(<范围>): <简短描述>

<详细描述>

<关联问题>
```

### 类型标识
- **feat**: 新功能
- **fix**: Bug修复
- **docs**: 文档更新
- **style**: 代码格式调整
- **refactor**: 代码重构
- **perf**: 性能优化
- **test**: 测试相关
- **chore**: 构建或辅助工具变动

### 示例
```bash
# 好的提交信息
git commit -m "feat(trading): 添加10:30早盘捕捉功能

- 实现实时数据推送
- 添加智能选股算法
- 集成AI分析模块

Closes #123"

# 不好的提交信息
git commit -m "update code"  # ❌ 太模糊
git commit -m "fix"          # ❌ 没有说明
```

## 🛡️ 分支保护规则

### main分支保护
- ✅ 需要PR才能合并
- ✅ 需要至少1人审查
- ✅ 需要通过CI测试
- ✅ 禁止强制推送
- ✅ 禁止删除

### develop分支保护
- ✅ 需要PR才能合并
- ✅ 需要通过CI测试
- ✅ 禁止强制推送

## 🏷️ 版本标签

### 标签命名
```bash
# 正式版本
v1.0.0

# 预发布版本
v1.0.0-beta.1
v1.0.0-rc.1

# 标记重要节点
sprint-3-completed
before-major-refactor
```

### 创建标签
```bash
# 创建带注释的标签
git tag -a v1.2.0 -m "Release version 1.2.0: 早盘捕捉功能"

# 推送标签
git push origin v1.2.0

# 推送所有标签
git push origin --tags
```

## 🔧 实用命令

### 查看分支
```bash
# 查看所有分支
git branch -a

# 查看远程分支
git branch -r

# 查看分支图
git log --graph --oneline --all
```

### 清理分支
```bash
# 删除本地分支
git branch -d feature/xxx

# 删除远程分支
git push origin --delete feature/xxx

# 清理已合并的分支
git branch --merged | grep -v "\*\|main\|develop" | xargs -n 1 git branch -d
```

### 同步分支
```bash
# 更新本地分支
git fetch origin
git checkout develop
git merge origin/develop

# 变基feature分支
git checkout feature/xxx
git rebase develop
```

## 📊 分支状态检查

### 每日检查
```bash
#!/bin/bash
# 检查未合并的分支
echo "未合并的功能分支:"
git branch -r --no-merged develop | grep feature/

echo "未合并的修复分支:"
git branch -r --no-merged develop | grep bugfix/

echo "活跃的分支（最近7天）:"
git for-each-ref --format='%(refname:short) %(committerdate)' refs/remotes | grep -v HEAD | awk '$2 >= "'$(date -d '7 days ago' '+%Y-%m-%d')'"'
```

## ⚠️ 注意事项

### Do's ✅
- 经常同步develop分支
- 小步提交，频繁推送
- 及时删除已合并分支
- 使用有意义的分支名
- 遵循提交信息规范

### Don'ts ❌
- 直接在main/develop开发
- 长期不合并的功能分支
- 强制推送到公共分支
- 在一个分支混合多个功能
- 忽视代码冲突

## 🚀 快速开始

```bash
# 克隆项目
git clone https://github.com/yourname/dongfengpo.git
cd dongfengpo

# 设置上游
git remote add upstream https://github.com/original/dongfengpo.git

# 创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/your-feature

# 开始开发...
```

---

*版本: v1.0*  
*更新日期: 2025-08-09*