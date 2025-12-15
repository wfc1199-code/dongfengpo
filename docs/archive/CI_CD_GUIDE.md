# CI/CD流水线指南

## 概述

东风破项目采用GitHub Actions实现自动化CI/CD流水线，支持自动测试、构建、部署等功能。

## 流水线架构

```
代码提交 → CI测试 → 构建镜像 → 部署到环境 → 健康检查 → 完成
```

## CI流水线

### 触发条件
- 推送到`main`或`develop`分支
- 创建Pull Request到`main`分支

### 工作流程

#### 1. 后端测试
- **语言版本**: Python 3.8, 3.9
- **测试内容**:
  - 代码格式检查 (flake8, black)
  - 类型检查 (mypy)
  - 单元测试 (pytest)
  - 测试覆盖率 (pytest-cov)

#### 2. 前端测试
- **语言版本**: Node.js 16.x, 18.x
- **测试内容**:
  - 代码质量检查 (ESLint)
  - 单元测试 (Jest)
  - 构建验证

#### 3. 安全扫描
- Python依赖安全扫描 (safety)
- Node.js依赖安全扫描 (npm audit)
- 容器镜像扫描 (Trivy)

#### 4. 版本备份
- 仅在`main`分支触发
- 自动创建版本快照
- 保留30天备份

## CD流水线

### 部署环境

#### Staging环境
- **触发条件**: 推送到`main`分支
- **部署地址**: https://staging.dongfengpo.com
- **自动部署**: 是

#### Production环境
- **触发条件**: 创建版本标签 (v*)
- **部署地址**: https://dongfengpo.com
- **需要审批**: 是

### 部署流程

1. **构建Docker镜像**
   ```bash
   docker build -t dongfengpo-backend:$SHA ./backend
   docker build -t dongfengpo-frontend:$SHA ./frontend
   ```

2. **推送到镜像仓库**
   ```bash
   docker push ghcr.io/your-org/dongfengpo/backend:$SHA
   docker push ghcr.io/your-org/dongfengpo/frontend:$SHA
   ```

3. **部署到服务器**
   - 使用SSH连接到目标服务器
   - 拉取最新镜像
   - 滚动更新服务
   - 执行健康检查

## 本地开发

### 运行CI测试
```bash
# 后端测试
cd backend
pytest tests/ -v --cov

# 前端测试
cd frontend
npm test

# 安全扫描
safety check -r backend/requirements.txt
npm audit
```

### 构建Docker镜像
```bash
# 使用docker-compose构建
docker-compose build

# 单独构建
docker build -t dongfengpo-backend ./backend
docker build -t dongfengpo-frontend ./frontend
```

### 本地部署
```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 健康检查
./scripts/health_check.sh
```

## 配置说明

### GitHub Secrets配置

需要在GitHub仓库设置以下Secrets：

#### 部署相关
- `STAGING_HOST`: Staging服务器地址
- `STAGING_USER`: Staging服务器用户名
- `STAGING_SSH_KEY`: Staging服务器SSH私钥
- `PROD_HOST`: 生产服务器地址
- `PROD_USER`: 生产服务器用户名
- `PROD_SSH_KEY`: 生产服务器SSH私钥

#### 可选配置
- `CODECOV_TOKEN`: Codecov上传令牌
- `SLACK_WEBHOOK`: Slack通知地址

### 环境变量

#### 后端环境变量
```env
DATABASE_URL=postgresql://user:password@db:5432/dongfengpo
REDIS_URL=redis://redis:6379/0
USE_REAL_DATA=true
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key
```

#### 前端环境变量
```env
REACT_APP_API_URL=http://localhost:9000
REACT_APP_WS_URL=ws://localhost:9000/ws
```

## 监控和告警

### 健康检查端点
- 后端健康检查: `/api/health`
- 前端健康检查: `/health`
- 监控指标: `/metrics`

### 日志查看
```bash
# 查看容器日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 查看应用日志
tail -f backend/logs/app.log
```

### 性能监控
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## 故障排查

### CI失败
1. 检查测试日志
2. 确认依赖版本
3. 本地复现问题

### CD失败
1. 检查部署日志
2. 验证服务器连接
3. 检查Docker服务状态
4. 运行健康检查脚本

### 回滚操作
```bash
# 查看部署历史
docker images | grep dongfengpo

# 回滚到上一个版本
docker-compose down
docker-compose up -d --scale backend=0 backend
docker tag dongfengpo-backend:previous dongfengpo-backend:latest
docker-compose up -d backend
```

## 最佳实践

1. **代码提交**
   - 使用有意义的提交信息
   - 保持小而频繁的提交
   - 运行本地测试后再提交

2. **分支管理**
   - `main`: 生产就绪代码
   - `develop`: 开发集成分支
   - `feature/*`: 功能开发分支
   - `hotfix/*`: 紧急修复分支

3. **版本发布**
   - 使用语义化版本号 (v1.2.3)
   - 创建Release Notes
   - 标记重要里程碑

4. **安全考虑**
   - 定期更新依赖
   - 扫描安全漏洞
   - 使用环境变量管理敏感信息

## 持续改进

- 定期审查CI/CD流程
- 收集团队反馈
- 优化构建时间
- 提升部署可靠性

---
*更新时间: 2025-08-19*