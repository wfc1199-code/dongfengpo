# 🚀 东风破 - 快速参考

## 📝 三种架构对比

| 特性 | Legacy单体 | **模块化单体** ⭐ | 完整微服务 |
|------|-----------|----------------|-----------|
| 复杂度 | ⭐ 简单 | ⭐⭐ 中等 | ⭐⭐⭐⭐⭐ 复杂 |
| 代码组织 | ❌ 混乱 | ✅ 清晰 | ✅ 清晰 |
| 部署难度 | ⭐ 简单 | ⭐ 简单 | ⭐⭐⭐⭐⭐ 困难 |
| 进程数 | 1 | 1 | 11+ |
| 性能 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 可扩展性 | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **推荐场景** | 已废弃 | **当前开发** | 未来生产 |

---

## 🎯 快速启动

### 方式1：模块化版本（推荐）

```bash
# 1. 停止旧服务
./scripts/stop_modular.sh

# 2. 启动新服务
./scripts/start_modular.sh

# 3. 访问
http://localhost:9000/docs
```

### 方式2：Legacy版本（备用）

```bash
cd backend
../venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 9000
```

---

## 📂 项目结构

```
东风破/
├── backend/
│   ├── modules/           # 📦 新：模块化架构
│   │   ├── limit_up/      # 涨停预测
│   │   ├── anomaly/       # 异动检测
│   │   ├── stocks/        # 股票数据
│   │   └── shared/        # 共享组件
│   ├── main_modular.py    # 🟢 新主程序
│   └── main.py            # 🔴 旧主程序
├── frontend/              # React前端
├── scripts/
│   ├── start_modular.sh   # 启动模块化版本
│   └── start_dongfeng.sh  # 启动Legacy版本
└── docs/
    ├── MODULAR_MONOLITH_GUIDE.md     # 详细指南
    └── REFACTORING_COMPLETE.md       # 重构报告
```

---

## 🔧 常用命令

### 启动/停止

```bash
# 模块化版本
./scripts/start_modular.sh
./scripts/stop_modular.sh

# Legacy版本
./scripts/start_dongfeng.sh
./scripts/stop_dongfeng.sh
```

### 测试

```bash
# 健康检查
curl http://localhost:9000/health

# 查看模块列表
curl http://localhost:9000/modules

# 测试涨停预测模块
curl http://localhost:9000/api/limit-up/health

# API文档
open http://localhost:9000/docs
```

### 前端

```bash
cd frontend
PORT=3000 npm start
```

---

## 📊 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| 后端 | 9000 | Legacy或Modular（二选一） |
| 前端 | 3000 | React开发服务器 |
| Redis | 6379 | 可选 |

---

## 🆘 故障排除

### 问题1：端口被占用

```bash
# 查找占用进程
lsof -i :9000

# 杀死进程
lsof -ti:9000 | xargs kill -9
```

### 问题2：前端Failed to fetch

```bash
# 检查.env.local配置
cat frontend/.env.local

# 确保是
REACT_APP_USE_API_GATEWAY=false
REACT_APP_API_URL=http://localhost:9000
```

### 问题3：模块加载失败

```bash
# 查看日志
tail -f logs/modular_backend.log
tail -f backend/logs/dongfeng_modular.log
```

---

## 📚 文档索引

| 文档 | 用途 |
|------|------|
| [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) | 本文档 - 快速参考 |
| [MODULAR_MONOLITH_GUIDE.md](./MODULAR_MONOLITH_GUIDE.md) | 模块化架构详细指南 |
| [REFACTORING_COMPLETE.md](./REFACTORING_COMPLETE.md) | 重构完成报告 |
| [MIGRATION_STATUS.md](./MIGRATION_STATUS.md) | 微服务迁移状态 |
| [README.md](./README.md) | 项目总览 |

---

## 🎯 下一步做什么？

### 如果你是开发者

1. ✅ 使用模块化版本开发新功能
2. ✅ 参考 `modules/limit_up/module.py` 示例
3. ✅ 阅读 `MODULAR_MONOLITH_GUIDE.md`

### 如果你是用户

1. ✅ 使用任一版本启动系统
2. ✅ 访问 http://localhost:3000
3. ✅ 正常使用所有功能

### 如果你是运维

1. ✅ 使用 `./scripts/start_modular.sh` 启动
2. ✅ 监控 `logs/` 目录下的日志
3. ✅ 设置自动重启（systemd/supervisor）

---

## 💡 关键决策

### 何时使用模块化版本？

✅ **推荐**：
- 开发新功能
- 重构现有代码
- 学习项目结构

❌ **不推荐**：
- 快速修复紧急bug（用Legacy）
- 生产环境（等迁移完成）

### 何时切换到微服务？

🎯 **触发条件**：
- 用户量 > 1000并发
- 某模块需要独立扩展
- 团队规模 > 5人

---

最后更新: 2025-10-02
版本: 2.0.0-modular
