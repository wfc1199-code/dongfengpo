# 🔄 服务重启指南

**日期**: 2025-12-15  
**原因**: 新端点迁移完成，需要重启服务加载新代码

---

## 📋 需要重启的服务

1. **Signal API** (端口 9001)
   - 新端点: `/api/anomaly/market-anomaly/scan`
   - 新端点: `/api/config/system/monitoring-stocks`

2. **API Gateway** (端口 8080)
   - 新端点: `/api/system/status`
   - 新路由配置

---

## 🔧 重启步骤

### 方法1: 使用启动脚本（推荐）

```bash
# 停止所有服务
pkill -f "python.*main.py" || true
pkill -f "uvicorn" || true

# 等待2秒
sleep 2

# 重新启动
./scripts/start_bmad_refactored.sh
```

### 方法2: 手动重启

```bash
# 1. 停止 Signal API
pkill -f "signal-api" || true

# 2. 停止 API Gateway
pkill -f "api-gateway" || true

# 3. 等待2秒
sleep 2

# 4. 启动 Signal API
cd services/signal-api
python main.py &
cd ../..

# 5. 启动 API Gateway
cd services/api-gateway
python main.py &
cd ../..
```

### 方法3: 如果使用 systemd 或 supervisor

```bash
# 重启服务
sudo systemctl restart signal-api
sudo systemctl restart api-gateway
```

---

## ✅ 验证重启成功

### 1. 检查服务健康状态

```bash
# API Gateway
curl http://localhost:8080/gateway/health

# Signal API
curl http://localhost:9001/health
```

### 2. 测试新端点

```bash
# 测试市场异动扫描
curl "http://localhost:8080/api/market-anomaly/scan?limit=5"

# 测试系统状态
curl http://localhost:8080/api/system/status

# 测试监控股票列表
curl http://localhost:8080/api/system/monitoring-stocks
```

### 3. 运行完整端点检查

```bash
python3 backend/tests/check_missing_endpoints.py
```

**预期结果**:
- ✅ `/api/market-anomaly/scan` - 存在
- ✅ `/api/system/status` - 存在
- ✅ `/api/system/monitoring-stocks` - 存在

---

## ⚠️ 注意事项

1. **数据不会丢失**: 重启不会影响Redis中的数据
2. **前端连接**: 前端可能需要刷新页面
3. **WebSocket**: 如果使用WebSocket，客户端需要重连

---

## 🐛 故障排查

### 如果端点仍然404

1. **检查服务是否启动**:
   ```bash
   ps aux | grep -E "(signal-api|api-gateway)"
   ```

2. **检查端口是否被占用**:
   ```bash
   lsof -i :8080
   lsof -i :9001
   ```

3. **检查日志**:
   ```bash
   tail -f logs/signal-api.log
   tail -f logs/api-gateway.log
   ```

4. **检查代码是否正确**:
   ```bash
   # 验证文件存在
   ls -la services/signal-api/signal_api/routers/anomaly.py
   ls -la services/api-gateway/main.py
   ```

---

**创建时间**: 2025-12-15

