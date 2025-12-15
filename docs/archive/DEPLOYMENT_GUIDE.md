# 东风破系统部署指南

## 🚀 快速部署

### 环境要求
- Docker 20.10+
- Docker Compose 2.0+
- Node.js 16+ (开发环境)
- Python 3.8+ (开发环境)

### 一键启动
```bash
# 克隆项目
git clone https://github.com/your-org/dongfengpo.git
cd dongfengpo

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 运行健康检查
./scripts/health_check.sh
```

## 📋 服务访问地址

| 服务 | 地址 | 用途 |
|------|------|------|
| 前端应用 | http://localhost | 主要界面 |
| 后端API | http://localhost:9000 | API服务 |
| API文档 | http://localhost:9000/docs | Swagger文档 |
| Grafana | http://localhost:3000 | 监控面板 (admin/admin) |
| Prometheus | http://localhost:9090 | 指标查询 |
| WebSocket | ws://localhost:9000/ws | 实时推送 |

## 🔧 配置说明

### 环境变量配置
创建 `.env` 文件：
```env
# 数据源配置
USE_REAL_DATA=false
TUSHARE_TOKEN=your_token_here
AKSHARE_ENABLED=true

# 数据库配置
DATABASE_URL=postgresql://user:password@db:5432/dongfengpo
REDIS_URL=redis://redis:6379/0

# 安全配置
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret

# 日志配置
LOG_LEVEL=INFO
LOG_FILE_PATH=./logs/app.log

# 监控配置
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
```

### 生产环境配置
```bash
# 复制生产配置模板
cp docker-compose.prod.yml docker-compose.override.yml

# 修改生产配置
vim docker-compose.override.yml
```

## 🔄 数据源配置

### 启用真实数据源
1. **获取Tushare Token**
   - 注册 https://tushare.pro/
   - 获取API Token
   - 设置环境变量 `TUSHARE_TOKEN`

2. **配置AkShare**
   ```bash
   # 安装AkShare (可选，已在Docker中包含)
   pip install akshare
   ```

3. **切换到真实数据**
   ```env
   USE_REAL_DATA=true
   ```

## 📊 功能验证

### 核心功能测试
```bash
# 1. 测试API健康状态
curl http://localhost:9000/api/health

# 2. 测试涨停预测功能
curl http://localhost:9000/api/limit-up-tracker/today

# 3. 测试异动检测
curl http://localhost:9000/api/anomaly/current

# 4. 测试WebSocket连接
wscat -c ws://localhost:9000/ws
```

### 前端功能验证
1. 访问 http://localhost
2. 检查各个面板是否正常加载
3. 测试股票搜索和图表显示
4. 验证实时数据更新

## 🚨 故障排查

### 常见问题

#### 1. 容器启动失败
```bash
# 查看日志
docker-compose logs backend
docker-compose logs frontend

# 重启服务
docker-compose restart backend
```

#### 2. 数据库连接失败
```bash
# 检查数据库状态
docker-compose exec db pg_isready

# 重建数据库
docker-compose down -v
docker-compose up -d db
```

#### 3. 前端页面无法访问
```bash
# 检查nginx配置
docker-compose exec frontend nginx -t

# 重启前端服务
docker-compose restart frontend
```

#### 4. API响应超时
```bash
# 检查后端资源使用
docker stats dongfengpo-backend

# 调整超时设置
export API_TIMEOUT=30
```

### 性能优化

#### 1. 数据库优化
```sql
-- 创建索引
CREATE INDEX idx_stocks_code ON stocks(code);
CREATE INDEX idx_anomalies_timestamp ON anomalies(timestamp);
```

#### 2. Redis缓存优化
```bash
# 设置Redis内存限制
docker-compose exec redis redis-cli CONFIG SET maxmemory 1gb
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

#### 3. 应用层优化
```python
# 调整worker数量
uvicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

## 🔐 安全配置

### SSL/TLS配置
```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/ssl/certs/dongfengpo.crt;
    ssl_certificate_key /etc/ssl/private/dongfengpo.key;
    
    # SSL安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
}
```

### 防火墙配置
```bash
# 只开放必要端口
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable
```

## 📈 监控配置

### 告警通知设置
编辑 `monitoring/alertmanager.yml`：
```yaml
receivers:
- name: 'team-alerts'
  email_configs:
  - to: 'alerts@your-company.com'
    subject: '东风破系统告警: {{ .GroupLabels.alertname }}'
    body: |
      告警详情:
      {{ range .Alerts }}
      - 告警: {{ .Annotations.summary }}
      - 描述: {{ .Annotations.description }}
      - 时间: {{ .StartsAt }}
      {{ end }}
```

### 自定义监控指标
在应用代码中添加：
```python
from prometheus_client import Counter, Histogram, Gauge

# 业务指标
trade_signals = Counter('trade_signals_total', 'Total trade signals generated')
prediction_accuracy = Gauge('prediction_accuracy_rate', 'Model prediction accuracy')
```

## 🔄 备份和恢复

### 数据备份
```bash
# 创建备份脚本
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T db pg_dump -U user dongfengpo > backup_${DATE}.sql
docker cp dongfengpo-redis:/data/dump.rdb redis_backup_${DATE}.rdb
EOF

chmod +x backup.sh
```

### 定时备份
```bash
# 添加crontab任务
crontab -e

# 每天凌晨2点备份
0 2 * * * /path/to/dongfengpo/backup.sh
```

## 🚀 生产部署建议

### 1. 负载均衡
```yaml
# nginx负载均衡配置
upstream backend {
    server backend1:9000;
    server backend2:9000;
    server backend3:9000;
}
```

### 2. 数据库主从
```yaml
# 数据库主从复制
services:
  db-master:
    image: postgres:15
    environment:
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: secret
  
  db-slave:
    image: postgres:15
    environment:
      PGUSER: postgres
      POSTGRES_MASTER_SERVICE: db-master
```

### 3. 服务监控
```bash
# 服务健康检查
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9000/api/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## 📚 运维手册

### 日常运维
1. **每日检查**
   - 运行健康检查脚本
   - 查看监控面板
   - 检查告警状态

2. **每周维护**
   - 清理旧日志文件
   - 更新系统补丁
   - 备份重要数据

3. **每月优化**
   - 分析性能指标
   - 优化数据库查询
   - 更新依赖包

### 应急预案
1. **服务中断**
   - 立即切换到备用服务
   - 查看错误日志
   - 通知相关人员

2. **数据异常**
   - 停止异常服务
   - 恢复最近备份
   - 分析异常原因

3. **性能下降**
   - 检查系统资源
   - 分析慢查询
   - 优化热点代码

---

## 📞 技术支持

- **文档**: 查看项目README和各模块文档
- **日志**: 检查 `logs/` 目录下的日志文件
- **监控**: 访问Grafana监控面板
- **健康检查**: 运行 `./scripts/health_check.sh`

---
*部署指南版本: v1.0*  
*更新时间: 2025-08-19*