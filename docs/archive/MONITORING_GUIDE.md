# 监控系统使用指南

## 概述

东风破项目配备了完整的监控系统，包括指标收集、可视化展示和告警通知功能。

## 系统架构

```
应用指标 → Prometheus → Grafana → 可视化展示
     ↓
   告警规则 → Alertmanager → 通知渠道
```

## 监控组件

### 1. Prometheus
- **功能**: 时序数据库，收集和存储指标
- **端口**: 9090
- **访问地址**: http://localhost:9090

### 2. Grafana
- **功能**: 数据可视化和仪表板
- **端口**: 3000
- **访问地址**: http://localhost:3000
- **默认账号**: admin/admin

### 3. Alertmanager
- **功能**: 告警管理和通知
- **端口**: 9093
- **访问地址**: http://localhost:9093

## 监控指标

### 系统指标
- CPU使用率
- 内存使用率
- 磁盘使用率
- 网络流量

### 应用指标
- API请求数
- API响应时间
- API错误率
- WebSocket连接数

### 数据库指标
- 连接池使用率
- 查询性能
- 慢查询数量

### Redis指标
- 内存使用率
- 命中率
- 连接数

## 告警规则

### 严重告警 (Critical)
- API服务下线超过1分钟
- 数据库连接失败
- 磁盘空间不足(<15%)

### 警告告警 (Warning)
- API响应时间>1秒
- 错误率>5%
- CPU使用率>80%
- 内存使用率>90%
- 数据库连接池>80%

## 使用指南

### 启动监控系统
```bash
# 启动所有监控组件
docker-compose up -d prometheus grafana alertmanager

# 验证服务状态
docker-compose ps
```

### 访问监控面板
1. 打开浏览器访问 http://localhost:3000
2. 使用 admin/admin 登录
3. 选择"东风破监控面板"

### 查看指标
```bash
# 查看所有指标
curl http://localhost:9000/metrics

# 查看健康状态
curl http://localhost:9000/api/health
```

### 配置告警通知

#### 邮件通知
编辑 `monitoring/alertmanager.yml`:
```yaml
receivers:
- name: 'critical'
  email_configs:
  - to: 'your-email@example.com'
    from: 'alerts@dongfengpo.com'
    smarthost: 'smtp.example.com:587'
    auth_username: 'username'
    auth_password: 'password'
```

#### Webhook通知
```yaml
receivers:
- name: 'warning'
  webhook_configs:
  - url: 'http://your-webhook-url/alerts'
```

## 故障排查

### 监控数据不更新
1. 检查Prometheus是否正常运行
2. 验证应用是否暴露指标端点
3. 检查网络连接

### 告警不触发
1. 检查告警规则配置
2. 验证Alertmanager服务状态
3. 查看Prometheus告警状态页面

### Grafana无法显示数据
1. 检查数据源配置
2. 验证Prometheus查询
3. 检查时间范围设置

## 性能优化建议

1. **数据保留策略**
   - Prometheus默认保留15天数据
   - 可通过`--storage.tsdb.retention.time`调整

2. **采样间隔**
   - 默认15秒采样一次
   - 高频指标可设置10秒
   - 低频指标可设置30秒

3. **资源限制**
   - 为监控容器设置资源限制
   - 避免影响主应用性能

## 自定义监控

### 添加新指标
在应用代码中:
```python
from prometheus_client import Counter, Histogram

# 计数器
request_count = Counter('my_requests_total', 'Total requests')

# 直方图
request_duration = Histogram('my_request_duration_seconds', 'Request duration')
```

### 创建新仪表板
1. 登录Grafana
2. 创建新Dashboard
3. 添加Panel
4. 配置查询和可视化

### 添加新告警
编辑 `monitoring/rules/alerts.yml`:
```yaml
- alert: MyCustomAlert
  expr: my_metric > 100
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "自定义告警触发"
```

## 最佳实践

1. **定期检查**
   - 每天查看监控面板
   - 及时处理告警
   - 分析性能趋势

2. **告警策略**
   - 避免告警疲劳
   - 设置合理阈值
   - 分级处理告警

3. **数据备份**
   - 定期备份Grafana配置
   - 导出重要仪表板
   - 保存告警规则

---
*更新时间: 2025-08-19*