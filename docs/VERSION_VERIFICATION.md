# 版本确认说明

## 📋 版本识别

### ✅ 重构后的模块化版本（新版本）

**文件**: `backend/main_modular.py`

**特征**:
- 导入语句: `from modules.xxx import XxxModule`
- 使用模块化架构: `modules/` 目录下的模块
- 应用标题: "东风破 - 模块化单体版"
- 版本号: "2.0.0"
- 日志文件: `logs/dongfeng_modular.log`

**启动命令**:
```bash
cd /Users/wangfangchun/东风破/backend
uvicorn main_modular:app --host 0.0.0.0 --port 9000
```

### ❌ 原始版本（已废弃）

**文件**: `backups/cleanup_20251002_102711/main_old.py`

**特征**:
- 导入语句: `from api.xxx import router`
- 使用单体架构: `api/` 目录下的路由文件
- 应用标题: "东风破 - AI异动拉升检测系统"
- 日志文件: `logs/dongfeng.log`

**状态**: 已备份，不应再使用

## 🔍 如何确认当前运行的版本

### 方法1: 检查导入语句

```bash
# 检查 main_modular.py 的导入
grep "from modules" backend/main_modular.py
# 应该看到: from modules.limit_up import LimitUpModule 等

# 检查是否有 api 导入（不应该有）
grep "from api\." backend/main_modular.py
# 应该没有结果
```

### 方法2: 检查API响应

```bash
# 访问根路径
curl http://localhost:9000/

# 新版本应该返回:
# {
#   "name": "东风破 - 模块化单体版",
#   "version": "2.0.0",
#   "architecture": "Modular Monolith",
#   ...
# }
```

### 方法3: 检查模块列表

```bash
# 访问模块列表
curl http://localhost:9000/modules

# 新版本应该返回模块列表:
# {
#   "total": 7,
#   "modules": [
#     {"name": "limit_up", "prefix": "/api/limit-up", ...},
#     {"name": "stocks", "prefix": "/api/stocks", ...},
#     ...
#   ]
# }
```

### 方法4: 检查日志文件

```bash
# 查看日志文件名
ls -la backend/logs/

# 新版本使用: dongfeng_modular.log
# 旧版本使用: dongfeng.log
```

## ✅ 确认清单

运行 Phase 2 测试前，请确认：

- [ ] 当前运行的是 `main_modular.py`（不是 `main.py`）
- [ ] 导入的是 `modules.xxx`（不是 `api.xxx`）
- [ ] API响应显示版本为 "2.0.0"
- [ ] `/modules` 端点返回模块列表
- [ ] 日志文件是 `dongfeng_modular.log`

## 🚨 如果发现运行的是旧版本

如果发现当前运行的是旧版本：

1. **停止旧服务**
   ```bash
   pkill -f "main.py"
   ```

2. **启动新版本**
   ```bash
   cd /Users/wangfangchun/东风破/backend
   uvicorn main_modular:app --host 0.0.0.0 --port 9000
   ```

3. **验证版本**
   ```bash
   curl http://localhost:9000/ | grep version
   # 应该显示: "version": "2.0.0"
   ```

---

**创建时间**: 2025-01-02  
**状态**: ✅ 已确认 `main_modular.py` 是重构后的新版本

