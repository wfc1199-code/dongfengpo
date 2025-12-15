# 优化后快速启动指南

**更新时间**: 2025-10-01 18:25
**系统状态**: ✅ 已优化
**预期性能**: CPU<5%, 响应<500ms

---

## 🚀 快速启动

### 方式1: 使用启动脚本（推荐）

```bash
# 停止旧服务
./scripts/stop_dongfeng.sh

# 启动优化后的服务
./scripts/start_dongfeng.sh
```

### 方式2: 手动启动

```bash
# 1. 启动后端
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 9000 --reload

# 2. 启动前端（新终端）
cd frontend
npm start
```

### 验证启动成功

```bash
# 检查健康状态
curl http://localhost:9000/health

# 预期输出:
# {
#   "status": "healthy",
#   "version": "v2.0",
#   ...
# }
```

---

## 🔍 监控检查

### 1. CPU占用检查

```bash
# 查看后端进程
top -pid $(pgrep -f uvicorn)

# 预期: CPU < 5% (无客户端连接时)
```

### 2. 日志检查

```bash
# 查看实时日志
tail -f logs/dongfeng.log

# 预期输出示例:
# 2025-10-01 18:00:00 [INFO] __main__:64 - 日志系统已启动
# 2025-10-01 18:00:01 [INFO] websocket_routes:25 - WebSocket客户端连接
```

### 3. 浏览器检查

打开浏览器访问: http://localhost:3000

**检查清单**:
- [ ] 页面正常加载（<3秒）
- [ ] 分时图正常显示
- [ ] 切换股票响应快速（<500ms）
- [ ] 控制台无错误日志
- [ ] WebSocket连接显示 ✅

---

## 🎯 性能基准

### 正常指标

| 指标 | 目标值 | 如何查看 |
|------|--------|----------|
| CPU占用 | <5% | `top -pid $(pgrep -f uvicorn)` |
| 内存占用 | <500MB | 同上 |
| 首屏加载 | <3秒 | 浏览器开发者工具 → Network |
| API响应 | <500ms | Network标签查看请求时间 |
| WebSocket延迟 | <100ms | Console标签查看时间戳 |

### 异常情况

如果指标超出目标：

**CPU > 10%**
```bash
# 检查后台任务
ps aux | grep python | grep uvicorn

# 查看日志
tail -100 logs/dongfeng.log | grep ERROR

# 重启服务
./scripts/stop_dongfeng.sh && ./scripts/start_dongfeng.sh
```

**API响应 > 1秒**
```bash
# 检查网络
curl -w "@curl-format.txt" http://localhost:9000/health

# 检查数据源
curl http://localhost:9000/health | jq '.data_sources'
```

**WebSocket断开**
```bash
# 检查端点
wscat -c ws://localhost:9000/ws

# 检查日志
grep "WebSocket" logs/dongfeng.log | tail -20
```

---

## 🛠️ 常用命令

### 服务管理

```bash
# 启动服务
./scripts/start_dongfeng.sh

# 停止服务
./scripts/stop_dongfeng.sh

# 重启服务
./scripts/stop_dongfeng.sh && ./scripts/start_dongfeng.sh

# 查看服务状态
ps aux | grep -E "(uvicorn|npm start)"
```

### 日志查看

```bash
# 实时日志
tail -f logs/dongfeng.log

# 查看错误
grep ERROR logs/dongfeng.log | tail -20

# 查看最近10分钟
grep "$(date -v-10M '+%Y-%m-%d %H:')" logs/dongfeng.log

# 统计错误数
grep ERROR logs/dongfeng.log | wc -l
```

### 健康检查

```bash
# 完整健康信息
curl http://localhost:9000/health | jq .

# 只看状态
curl -s http://localhost:9000/health | jq -r '.status'

# 检查Redis
curl -s http://localhost:9000/health | jq -r '.redis'

# 检查数据源
curl -s http://localhost:9000/health | jq '.data_sources'
```

### 性能测试

```bash
# API响应时间
time curl http://localhost:9000/api/stocks/sz000001/timeshare

# 并发测试（需要ab工具）
ab -n 100 -c 10 http://localhost:9000/health

# WebSocket测试
wscat -c ws://localhost:9000/ws
```

---

## 📋 配置文件位置

### 后端配置

```bash
backend/
├── .env                      # 环境变量（可选）
├── data/config.json          # 用户配置
└── logs/
    └── dongfeng.log          # 主日志文件
```

**环境变量**:
```bash
# 创建 backend/.env
LOG_LEVEL=INFO              # 日志级别
API_HOST=0.0.0.0           # API监听地址
API_PORT=9000              # API端口
```

### 前端配置

```bash
frontend/
├── .env.local               # 环境配置（已创建）
└── src/config.ts            # API地址配置
```

**当前配置**:
```bash
REACT_APP_USE_API_GATEWAY=false
REACT_APP_API_URL=http://localhost:9000
REACT_APP_DEBUG_MODE=false
```

---

## 🔧 故障排查

### 问题1: 服务启动失败

```bash
# 检查端口占用
lsof -i :9000
lsof -i :3000

# 杀掉占用进程
kill $(lsof -t -i :9000)
kill $(lsof -t -i :3000)

# 重新启动
./scripts/start_dongfeng.sh
```

### 问题2: 页面空白

```bash
# 清除前端缓存
cd frontend
rm -rf node_modules/.cache
npm start

# 清除浏览器缓存
# Chrome: Cmd+Shift+R (Mac) 或 Ctrl+Shift+R (Windows)
```

### 问题3: 数据不更新

```bash
# 检查后端健康
curl http://localhost:9000/health

# 检查WebSocket
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://localhost:9000/ws

# 查看错误日志
tail -50 logs/dongfeng.log | grep ERROR
```

### 问题4: CPU占用高

```bash
# 1. 检查后台任务
ps aux | grep python

# 2. 查看日志是否有循环错误
tail -100 logs/dongfeng.log

# 3. 重启服务
./scripts/stop_dongfeng.sh
./scripts/start_dongfeng.sh
```

---

## 📊 功能测试清单

### 基础功能

- [ ] 页面正常打开
- [ ] 自选股列表显示
- [ ] 点击股票切换
- [ ] 分时图显示
- [ ] K线图显示
- [ ] 支撑压力位显示

### 实时功能

- [ ] WebSocket连接成功
- [ ] 数据自动刷新
- [ ] 异动提醒
- [ ] 涨停监控

### 性能检查

- [ ] 首屏加载 < 3秒
- [ ] 股票切换 < 500ms
- [ ] 无404错误
- [ ] 无连接错误
- [ ] CPU < 5%

---

## 📚 文档索引

### 必读文档

1. **FINAL_OPTIMIZATION_SUMMARY.md** - 本次优化总结
2. **PROJECT_COMPREHENSIVE_ANALYSIS_2025.md** - 完整诊断报告
3. **README.md** - 项目说明

### 问题排查

1. **CONNECTION_FIX_REPORT.md** - 连接问题修复
2. **API_PATH_FIX.md** - API路径优化
3. **OPTIMIZATION_EXECUTION_REPORT.md** - 优化详情

### 参考资料

1. **backend/core/logging_config.py** - 日志配置示例
2. **frontend/.env.local** - 环境配置示例
3. **scripts/start_dongfeng.sh** - 启动脚本

---

## 🎯 下一步

### 今天

1. ✅ 重启服务验证优化效果
2. ✅ 监控1小时，观察CPU和内存
3. ✅ 测试所有核心功能

### 本周

1. [ ] 清理旧日志文件
2. [ ] 配置监控告警
3. [ ] 补充单元测试

### 本月

1. [ ] 决定架构方向（Legacy/Pipeline/混合）
2. [ ] 性能优化第二阶段
3. [ ] 建立监控体系

---

## 💡 提示

### 性能监控

```bash
# 创建监控脚本
cat > scripts/monitor.sh << 'EOF'
#!/bin/bash
while true; do
  echo "=== $(date) ==="
  echo "CPU: $(top -l 1 -pid $(pgrep -f uvicorn) -stats cpu | tail -1)"
  echo "Health: $(curl -s http://localhost:9000/health | jq -r '.status')"
  echo ""
  sleep 60
done
EOF

chmod +x scripts/monitor.sh
./scripts/monitor.sh
```

### 自动化健康检查

```bash
# 添加到crontab
*/5 * * * * curl -f http://localhost:9000/health || echo "Backend unhealthy" | mail -s "Alert" admin@example.com
```

---

**文档版本**: v1.0
**最后更新**: 2025-10-01 18:25
**适用版本**: 优化后v2.0
