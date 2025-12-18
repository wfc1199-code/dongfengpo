# Git 工作流快速指南

## 🚀 开始新功能开发

```bash
# 1. 确保main分支是最新的
git checkout main
git pull origin main

# 2. 创建功能分支（命名规范: <type>/<ticket-id>-<description>）
git checkout -b feature/DFP-101-backtest-engine

# 3. 开发过程中经常提交
git add .
git commit -m "feat(backtest): add executor scaffold"
git push origin feature/DFP-101-backtest-engine

# 4. 保持与main同步（建议每天一次）
git checkout main
git pull origin main
git checkout feature/DFP-101-backtest-engine
git rebase main  # 或 git merge main
git push -f origin feature/DFP-101-backtest-engine  # 如果用了rebase需要-f
```

## 📝 提交代码规范

```bash
# 使用 Conventional Commits 格式
git commit -m "type(scope): subject"

# 示例:
git commit -m "feat(backtest): add genetic algorithm optimizer"
git commit -m "fix(radar): resolve crash on empty data"
git commit -m "docs(readme): update installation guide"
```

**Type 类型**:

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/配置

## 🔍 提交前检查

```bash
# 1. 代码格式化
black .                          # Python
cd frontend && npm run format    # TypeScript

# 2. Lint检查
ruff check .                     # Python
cd frontend && npm run lint      # TypeScript

# 3. 运行测试
pytest                           # Python
cd frontend && npm test          # TypeScript

# 4. 类型检查
mypy services/                   # Python
cd frontend && npm run type-check  # TypeScript
```

## 🎯 创建 Pull Request

```bash
# 1. 推送到远程
git push origin feature/DFP-101-backtest-engine

# 2. 在GitHub上创建PR
# - 标题格式: [Feature] Add backtest engine
# - 填写PR模板中的所有必填项
# - 关联相关Issue
# - 请求代码审查

# 3. 根据审查意见修改
git add .
git commit -m "fix: address review comments"
git push origin feature/DFP-101-backtest-engine
```

## ✅ 合并后清理

```bash
# PR合并后删除本地和远程分支
git checkout main
git pull origin main
git branch -d feature/DFP-101-backtest-engine
git push origin --delete feature/DFP-101-backtest-engine
```

## 🔥 紧急修复流程

```bash
# 1. 从main创建hotfix分支
git checkout main
git pull origin main
git checkout -b hotfix/DFP-999-critical-bug

# 2. 快速修复并测试
# ... 修复代码 ...
git add .
git commit -m "fix: resolve critical bug"
git push origin hotfix/DFP-999-critical-bug

# 3. 创建PR，标记为Hotfix
# 4. 审查通过后立即合并和部署
```

## 💡 常用命令

```bash
# 查看状态
git status                       # 查看当前状态
git diff                         # 查看未暂存的改动
git diff --staged                # 查看暂存的改动
git log --oneline                # 查看提交历史

# 撤销操作
git restore <file>               # 撤销工作区的改动
git restore --staged <file>      # 取消暂存
git reset HEAD~1                 # 撤销最后一次提交（保留改动）
git reset --hard HEAD~1          # 撤销最后一次提交（丢弃改动）⚠️

# 分支操作
git branch                       # 查看本地分支
git branch -a                    # 查看所有分支（包括远程）
git branch -d <branch>           # 删除本地分支
git push origin --delete <branch> # 删除远程分支

# Stash（临时保存）
git stash                        # 临时保存当前改动
git stash pop                    # 恢复stash的改动
git stash list                   # 查看所有stash
```

## ⚠️ 常见问题

### Q: 如何撤销已 push 的 commit？

```bash
# 方法1: reset后强制push（仅自己的分支可用）
git reset --hard HEAD~1
git push -f origin <branch>

# 方法2: revert创建新提交（推荐）
git revert <commit-hash>
git push origin <branch>
```

### Q: 如何解决 merge 冲突？

```bash
# 1. 更新main
git checkout main
git pull origin main

# 2. 合并到功能分支
git checkout feature/xxx
git merge main

# 3. 解决冲突（编辑冲突文件）
# 4. 标记为已解决
git add <resolved-file>
git commit -m "chore: resolve merge conflicts"
git push origin feature/xxx
```

### Q: 如何修改最后一次 commit message？

```bash
git commit --amend -m "new message"
git push -f origin <branch>  # 如果已push需要强制推送
```

### Q: 如何合并多个 commit？

```bash
# 合并最近3个commit
git rebase -i HEAD~3
# 在编辑器中将后面的commit标记为squash
# 保存后编辑新的commit message
git push -f origin <branch>
```

---

**提示**: 遵循这些规范可以保持代码库整洁，提升团队协作效率！
