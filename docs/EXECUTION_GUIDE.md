# 🚀 删除旧版本执行指南

**执行日期**: 2025-12-15  
**预计时间**: 约1小时

---

## 📋 执行步骤

### 步骤1: 前端功能测试 (30分钟) ⭐⭐⭐⭐

#### 1.1 打开前端应用

访问: http://localhost:3000

#### 1.2 测试 MarketAnomalyScanner 组件

**操作**:
1. 找到包含"市场异动扫描"的页面/组件
2. 检查组件是否正常显示
3. 检查是否显示异动股票列表
4. 检查统计数据（极强、强势、活跃数量）
5. 打开浏览器 Console (F12)，检查是否有错误

**预期结果**:
- ✅ 组件正常显示
- ✅ 数据正常加载
- ✅ 无 Console 错误

#### 1.3 测试 ManagementDashboard - 系统状态

**操作**:
1. 打开"管理面板"或"系统管理"页面
2. 找到"系统状态"部分
3. 检查系统状态是否显示
4. 检查各服务健康状态
5. 检查 Console 是否有错误

**预期结果**:
- ✅ 系统状态正常显示
- ✅ 服务健康状态正确
- ✅ 无 Console 错误

#### 1.4 测试 ManagementDashboard - 监控股票列表

**操作**:
1. 在"管理面板"中找到"监控股票"部分
2. 检查用户自选股列表
3. 检查热门板块股票列表
4. 检查股票数量统计
5. 检查 Console 是否有错误

**预期结果**:
- ✅ 监控股票列表正常显示
- ✅ 数据正常加载
- ✅ 无 Console 错误

#### 1.5 测试结果记录

在 `docs/DELETION_EXECUTION_LOG.md` 中记录测试结果

---

### 步骤2: 创建备份 (20分钟) ⭐⭐⭐⭐⭐

#### 2.1 运行备份脚本

```bash
cd /Users/wangfangchun/东风破
./scripts/archive_legacy_backend.sh
```

#### 2.2 Git提交

```bash
# 添加备份文件
git add backups/backend-legacy-*/

# 提交
git commit -m "feat: archive backend v2.0.0 before deletion

- Backup main_modular.py and modules/
- BMAD refactored version is stable
- Ready to delete legacy backend"

# 创建标签
git tag -a v2.0.0-archived -m "Backend modular version archived before deletion"
```

#### 2.3 验证备份

```bash
# 检查备份目录
ls -lh backups/backend-legacy-*/

# 检查备份内容
cat backups/backend-legacy-*/BACKUP_INFO.md
```

---

### 步骤3: 删除 v2.0.0 (10分钟) ⭐⭐⭐⭐⭐

#### 3.1 安全删除（重命名方式）

```bash
cd /Users/wangfangchun/东风破

# 重命名 backend 目录（安全方式）
mv backend backend.deleted.$(date +%Y%m%d)

# 或者直接删除（如果确认）
# rm -rf backend/main_modular.py
# rm -rf backend/modules/
```

#### 3.2 立即验证

```bash
# 验证 Gateway
curl http://localhost:8080/gateway/health

# 验证 Signal API
curl http://localhost:9001/health

# 验证3个端点
curl "http://localhost:8080/api/market-anomaly/scan?limit=3"
curl http://localhost:8080/api/system/status
curl http://localhost:8080/api/system/monitoring-stocks

# 验证前端（浏览器访问）
# http://localhost:3000
```

#### 3.3 记录删除结果

在 `docs/DELETION_EXECUTION_LOG.md` 中记录删除结果

---

### 步骤4: 监控稳定性 (3-5天)

#### 4.1 日常检查

```bash
# 检查服务健康
curl http://localhost:8080/gateway/health

# 检查日志
tail -f logs/api-gateway.log
tail -f logs/signal-api.log
```

#### 4.2 监控指标

- API响应时间
- 错误率
- 服务健康状态
- 前端功能可用性

#### 4.3 确认无回退需求

- [ ] 系统运行稳定
- [ ] 无功能缺失
- [ ] 无性能问题
- [ ] 前端功能正常

---

### 步骤5: 删除 v1.0.0 backup (可选)

**前提**: 确认BMAD版本稳定运行3-5天

```bash
# 可选：永久保留作为历史参考
# 或者删除：
rm -rf backups/cleanup_20251002_102711/
```

---

## ⚠️ 注意事项

1. **备份优先**: 删除前必须创建完整备份
2. **验证及时**: 删除后立即验证系统运行
3. **监控持续**: 删除后持续监控3-5天
4. **回滚准备**: 保留备份至少30天

---

## 📝 执行记录

在 `docs/DELETION_EXECUTION_LOG.md` 中记录每个步骤的执行结果

---

**创建时间**: 2025-12-15

