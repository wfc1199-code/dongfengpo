# Commit Message 格式指南

## 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

## Type 类型

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 添加测试
- `chore`: 构建、配置等
- `revert`: 回滚

## Scope 范围示例

后端: `backtest`, `optimizer`, `radar`, `signal`, `gateway`, `strategy`
前端: `ui`, `page`, `chart`, `api`
通用: `config`, `deps`, `ci`

## 示例

```
feat(backtest): add genetic algorithm optimizer

- Implement population initialization
- Add fitness evaluation function
- Implement crossover and mutation operators

Closes #101
```

```
fix(radar): resolve data missing issue

Fixed by adding null check before processing data.

Fixes #202
```

```
docs(readme): update installation guide

Added Docker installation instructions.
```

## 工具

可以使用 commitizen 工具辅助生成规范的提交信息：

```bash
npm install -g commitizen cz-conventional-changelog
git cz
```
