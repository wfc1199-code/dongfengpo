# 期权数据层迁移计划

## 📋 什么是迁移计划？

迁移计划就是**如何安全地从旧代码切换到新代码的详细步骤**。

### 为什么需要迁移计划？

现在的情况：
- **旧代码**：`modules/options/service.py`（有问题，但正在运行）
- **新代码**：`modules/options/data_layer/`（解决了问题，但还没接入）

如果直接替换，风险很大：
- ❌ 系统可能崩溃
- ❌ 用户访问出错  
- ❌ 无法快速恢复

迁移计划让你**平滑过渡**，逐步切换，随时可以回滚。

---

## 🎯 迁移目标

1. ✅ 不影响现有用户使用
2. ✅ 逐步验证新代码正确性
3. ✅ 随时可以回退到旧代码
4. ✅ 最终完全切换到新代码

---

## 📅 迁移时间表

### 总览

| 阶段 | 时间 | 内容 | 风险 |
|-----|------|------|------|
| 阶段0 | 0.5天 | 环境准备 | 低 |
| 阶段1 | 1-2天 | 功能验证 | 低 |
| 阶段2 | 2-3天 | 并行运行 | 低 |
| 阶段3 | 3-5天 | 灰度切换 | 中 |
| 阶段4 | 1-2天 | 全量切换 | 中 |
| 阶段5 | 1天 | 清理旧代码 | 低 |

**总计：8-13天**

---

## 阶段0：环境准备（0.5天）

### 目标
确保新代码可以运行

### 步骤

```bash
# 1. 检查新代码是否存在
ls -la /Users/wangfangchun/东风破/backend/modules/options/data_layer/

# 2. 测试新代码能否导入
cd /Users/wangfangchun/东风破/backend
python3 -c "from modules.options.data_layer import option_data_service; print('✅ 导入成功')"

# 3. 检查旧代码是否正常
python3 -c "from modules.options.service import OptionsService; print('✅ 旧代码正常')"
```

### 检查点
- [ ] 新代码文件存在
- [ ] 新代码可以导入
- [ ] 旧代码仍然正常

### 遇到问题？
如果导入失败，检查：
1. Python版本是否正确（需要3.7+）
2. 依赖包是否安装（aiohttp）

---

## 阶段1：功能验证（1-2天）

### 目标
验证新代码的每个功能都能正常工作

### 步骤

```bash
cd /Users/wangfangchun/东风破/backend

# 1. 运行单元测试
python3 -m modules.options.data_layer.test_data_layer
# 预期：大部分测试通过

# 2. 运行使用示例
python3 -m modules.options.data_layer.example_usage
# 预期：能看到期权数据输出

# 3. 测试单个功能
python3 -c "
import asyncio
from modules.options.data_layer import option_data_service

async def test():
    # 测试搜索
    result = await option_data_service.search_options('510300', 3)
    print(f'搜索结果: {result[\"count\"]}个期权')
    
    # 测试行情
    if result['options']:
        code = result['options'][0]['code']
        quote = await option_data_service.get_option_quote(code)
        print(f'行情: {quote.get(\"status\")}')
    
    await option_data_service.close()

asyncio.run(test())
"
```

### 检查点
- [ ] 能搜索期权
- [ ] 能获取行情
- [ ] 能获取分时数据
- [ ] 能获取日K线
- [ ] 能获取5分钟K线
- [ ] 能获取15分钟K线

### 记录结果

创建测试记录：
```bash
# 创建测试日志
echo "阶段1功能验证 - $(date)" > migration_test_log.txt
python3 -m modules.options.data_layer.example_usage >> migration_test_log.txt 2>&1
```

---

## 阶段2：并行运行（2-3天）

### 目标
新旧代码同时运行，对比结果

### 步骤

```bash
# 1. 运行对比测试
cd /Users/wangfangchun/东风破/backend
python3 test_migration_comparison.py

# 预期输出：
# - 搜索结果基本一致
# - 分时数据数量相近（新代码可能略少，因为清理了异常数据）
# - K线数据基本一致
# - 新代码数据质量更好
```

### 对比内容

1. **功能对比**
   - 搜索功能：结果是否一致
   - 行情数据：价格是否相同
   - 分时数据：数据点数是否合理
   - K线数据：OHLC是否正确

2. **性能对比**
   ```bash
   # 测试响应时间
   time python3 -c "
   import asyncio
   from modules.options.service import OptionsService
   
   async def test():
       service = OptionsService()
       await service.get_minute_data('10005854')
   
   asyncio.run(test())
   "
   
   time python3 -c "
   import asyncio
   from modules.options.data_layer import option_data_service
   
   async def test():
       await option_data_service.get_minute_data('10005854')
       await option_data_service.close()
   
   asyncio.run(test())
   "
   ```

3. **数据质量对比**
   - 异常数据点数量
   - 是否有假数据
   - 涨跌幅是否合理

### 检查点
- [ ] 搜索结果基本一致
- [ ] 分时数据可用
- [ ] K线数据正确
- [ ] 新代码性能不差于旧代码
- [ ] 新代码数据质量更好

### 发现问题？

如果新代码有问题：
1. 记录问题现象
2. 检查是否是数据源问题（东方财富API）
3. 查看日志输出
4. 暂不切换，继续排查

---

## 阶段3：灰度切换（3-5天）

### 目标
部分接口使用新代码，观察效果

### 方案A：创建新路由（推荐）

在 `modules/options/module.py` 中添加新路由：

```python
# 新增路由 - 使用新数据层
from .data_layer import option_data_service

@router.get("/v2/search")
async def search_options_v2(keyword: str, limit: int = 10):
    """搜索期权 - 新版本"""
    return await option_data_service.search_options(keyword, limit)

@router.get("/v2/{option_code}/quote")
async def get_quote_v2(option_code: str):
    """获取行情 - 新版本"""
    return await option_data_service.get_option_quote(option_code)

@router.get("/v2/{option_code}/minute")
async def get_minute_v2(option_code: str):
    """获取分时数据 - 新版本"""
    return await option_data_service.get_minute_data(option_code)

@router.get("/v2/{option_code}/kline")
async def get_kline_v2(option_code: str, period: str = "daily", limit: int = 60):
    """获取K线 - 新版本"""
    return await option_data_service.get_kline_data(option_code, period, limit)
```

### 测试新路由

```bash
# 假设后端运行在 http://localhost:8000

# 测试搜索（新接口）
curl "http://localhost:8000/api/options/v2/search?keyword=510300&limit=5"

# 测试行情（新接口）
curl "http://localhost:8000/api/options/v2/10005854/quote"

# 测试分时（新接口）
curl "http://localhost:8000/api/options/v2/10005854/minute"

# 测试K线（新接口）
curl "http://localhost:8000/api/options/v2/10005854/kline?period=5min"
```

### 方案B：替换部分功能

如果想直接替换某个功能：

```python
# modules/options/service.py

class OptionsService:
    
    def __init__(self):
        # 导入新服务
        from .data_layer import option_data_service
        self.new_service = option_data_service
    
    async def get_kline_data(self, option_code: str, period: str, limit: int):
        """
        获取K线数据
        使用新数据层实现
        """
        # 直接使用新服务
        return await self.new_service.get_kline_data(option_code, period, limit)
```

### 检查点
- [ ] 新接口可以访问
- [ ] 返回数据格式正确
- [ ] 前端可以正常显示
- [ ] 没有明显错误

### 观察期

运行2-3天，观察：
1. **错误日志**：是否有异常报错
2. **性能监控**：响应时间是否正常
3. **用户反馈**：是否有用户投诉
4. **数据正确性**：K线图是否正常

---

## 阶段4：全量切换（1-2天）

### 目标
所有接口都使用新代码

### 步骤

1. **备份旧代码**

```bash
cd /Users/wangfangchun/东风破/backend/modules/options

# 备份旧文件
cp service.py service.py.backup
cp module.py module.py.backup

echo "✅ 已备份旧代码"
```

2. **修改路由**

修改 `modules/options/module.py`：

```python
from .data_layer import option_data_service

# 搜索期权
@router.get("/search")
async def search_options(keyword: str, limit: int = 10):
    return await option_data_service.search_options(keyword, limit)

# 获取行情
@router.get("/{option_code}/quote")
async def get_quote(option_code: str):
    return await option_data_service.get_option_quote(option_code)

# 获取分时数据
@router.get("/{option_code}/minute")
async def get_minute(option_code: str):
    return await option_data_service.get_minute_data(option_code)

# 获取K线数据
@router.get("/{option_code}/kline")
async def get_kline(option_code: str, period: str = "daily", limit: int = 60):
    return await option_data_service.get_kline_data(option_code, period, limit)
```

3. **重启服务**

```bash
# 停止旧服务
pkill -f "python.*main_modular.py"

# 启动新服务
cd /Users/wangfangchun/东风破/backend
python3 main_modular.py &

# 查看日志
tail -f logs/app.log
```

4. **快速验证**

```bash
# 测试主要功能
curl "http://localhost:8000/api/options/search?keyword=510300"
curl "http://localhost:8000/api/options/10005854/minute"
curl "http://localhost:8000/api/options/10005854/kline?period=5min"
```

### 检查点
- [ ] 服务启动成功
- [ ] 接口可以访问
- [ ] 返回数据正常
- [ ] 前端显示正常

### 出问题怎么办？

**回滚方案**：

```bash
# 1. 停止服务
pkill -f "python.*main_modular.py"

# 2. 恢复旧代码
cd /Users/wangfangchun/东风破/backend/modules/options
cp service.py.backup service.py
cp module.py.backup module.py

# 3. 重启服务
cd /Users/wangfangchun/东风破/backend
python3 main_modular.py &

echo "✅ 已回滚到旧版本"
```

---

## 阶段5：清理旧代码（1天）

### 目标
删除或归档不再使用的旧代码

### 步骤

```bash
cd /Users/wangfangchun/东风破/backend

# 1. 创建归档目录
mkdir -p archived/option_old_code_$(date +%Y%m%d)

# 2. 归档旧文件（不是删除，是移动到归档目录）
mv core/real_option_data_source.py archived/option_old_code_$(date +%Y%m%d)/
mv core/option_kline_generator.py archived/option_old_code_$(date +%Y%m%d)/
mv core/option_data_validator.py archived/option_old_code_$(date +%Y%m%d)/
mv modules/options/service.py.backup archived/option_old_code_$(date +%Y%m%d)/
mv modules/options/module.py.backup archived/option_old_code_$(date +%Y%m%d)/

# 3. 更新文档
echo "# 旧代码已归档到 archived/option_old_code_$(date +%Y%m%d)/" > MIGRATION_COMPLETE.md
echo "迁移完成时间: $(date)" >> MIGRATION_COMPLETE.md

echo "✅ 旧代码已归档"
```

### 检查点
- [ ] 旧代码已归档（不是删除）
- [ ] 系统仍然正常运行
- [ ] 文档已更新

---

## 📊 迁移检查清单

### 每个阶段完成后检查

- [ ] **功能正常**：所有接口都能访问
- [ ] **数据正确**：返回的数据合理
- [ ] **性能正常**：响应时间可接受
- [ ] **日志正常**：没有大量错误
- [ ] **用户满意**：没有投诉

### 最终验收

- [ ] 分时图不再有延迟问题
- [ ] 非交易日不会产生K线
- [ ] 5分钟K线数据正确
- [ ] 15分钟K线数据正确
- [ ] 数据来源清晰标识
- [ ] 旧代码已归档

---

## 🚨 风险和应对

### 风险1：新代码有bug

**应对**：
- 阶段2充分测试
- 阶段3小范围灰度
- 准备好回滚方案

### 风险2：性能下降

**应对**：
- 对比测试响应时间
- 必要时添加缓存
- 优化慢查询

### 风险3：数据不一致

**应对**：
- 详细对比测试
- 记录差异原因
- 确认是改进还是问题

### 风险4：用户投诉

**应对**：
- 提前通知用户
- 准备客服话术
- 快速响应反馈

---

## 📞 遇到问题？

### 常见问题

**Q: 新代码导入失败？**
A: 检查Python版本和依赖包

**Q: 数据量变少了？**
A: 正常，新代码会清理异常数据

**Q: 性能变慢了？**
A: 检查网络和API调用，添加日志排查

**Q: 前端显示异常？**
A: 检查返回数据格式，确认字段名称

### 回滚决策

出现以下情况立即回滚：
- ❌ 大量接口报错（>10%）
- ❌ 响应时间超过10秒
- ❌ 用户投诉激增
- ❌ 数据完全错误

---

## 📝 总结

迁移计划就是：
1. **先测试**：确保新代码能用
2. **再对比**：新旧代码结果一致
3. **灰度切换**：部分用户先用新代码
4. **全量切换**：所有用户用新代码
5. **清理归档**：旧代码归档备份

**核心原则**：小步快跑，随时可回滚！

---

## 📅 执行时间建议

- **工作日进行**：避免周末无人处理问题
- **避开高峰**：选择交易时间之外
- **留出缓冲**：每个阶段多留1-2天

**建议时间**：周一到周五，上午10点到下午5点

---

**准备好开始迁移了吗？从阶段0开始！**
