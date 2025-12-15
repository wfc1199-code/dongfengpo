# 东方财富API连接问题 - 最终诊断报告

## 问题现象

板块热度和市场扫描器返回模拟数据,无法获取真实数据。

## 根本原因

**系统级代理软件拦截了所有到东方财富API的HTTP/HTTPS连接**

### 证据

1. **DNS解析异常**:
   ```bash
   $ nslookup push2.eastmoney.com
   Address: 198.18.0.12  # 典型的代理分配IP
   ```

2. **TCP连接成功但HTTP失败**:
   ```bash
   $ curl http://push2.eastmoney.com/api/...
   * Connected to push2.eastmoney.com (198.18.0.12) port 80
   * Empty reply from server  # ← 关键问题
   ```

3. **所有东方财富端点都失败**:
   - ❌ http://push2.eastmoney.com
   - ❌ http://17.push2.eastmoney.com
   - ❌ http://23.push2.eastmoney.com
   - ❌ https://79.push2.eastmoney.com
   - ❌ https://push2ex.eastmoney.com

4. **只有特定接口成功**:
   - ✅ `ak.stock_zt_pool_em()` - 使用https://push2ex.eastmoney.com/getTopicZTPool

### 技术分析

IP地址198.18.0.0/15是IANA保留的基准测试地址段,常被Clash/Surge等代理软件用于:
- 透明代理
- DNS劫持
- 流量过滤

## 解决方案

### ⭐ 方案1: 关闭代理软件(临时)

最快的验证方法:

```bash
# 1. 完全退出ClashX/Surge/Shadowrocket等代理软件
# 2. 测试连接
curl "http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=3&fields=f12,f14"

# 如果成功返回JSON数据,说明就是代理软件问题
```

### ⭐⭐ 方案2: 配置代理规则(推荐)

如果您使用**ClashX**,编辑配置文件添加:

```yaml
rules:
  # 东方财富直连规则
  - DOMAIN-SUFFIX,eastmoney.com,DIRECT
  - DOMAIN,push2.eastmoney.com,DIRECT
  - DOMAIN,push2ex.eastmoney.com,DIRECT
  - DOMAIN,79.push2.eastmoney.com,DIRECT
  - DOMAIN,17.push2.eastmoney.com,DIRECT
  - DOMAIN,23.push2.eastmoney.com,DIRECT
```

如果您使用**Surge**:

```
[Rule]
DOMAIN-SUFFIX,eastmoney.com,DIRECT
DOMAIN,push2.eastmoney.com,DIRECT
```

配置后**重启代理软件**。

### 方案3: 修改系统hosts文件(不推荐)

```bash
# 获取真实IP(可能不稳定)
nslookup push2.eastmoney.com 114.114.114.114

# 添加到/etc/hosts
sudo vim /etc/hosts
# 添加: <真实IP> push2.eastmoney.com
```

### 方案4: 完全重构数据源(最后选择)

如果网络问题无法解决,需要重构系统使用其他数据源:
- Tushare Pro(付费,稳定)
- 新浪财经(免费但字段少)
- 腾讯财经(免费但速度慢)

## 验证步骤

修改配置后,运行以下命令验证:

```bash
# 1. 测试curl
curl "http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=3&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6&fields=f12,f14,f2,f3"

# 应该返回JSON格式的股票数据

# 2. 测试Python代码
cd /Users/wangfangchun/东风破/backend
venv/bin/python -c "
import asyncio
import sys
sys.path.insert(0, 'backend')

async def test():
    from modules.market_scanner.service import MarketScannerService
    service = MarketScannerService()
    result = await service.scan_market('top_gainers', 3)
    print(f'数据源: {result.get(\"data\", {}).get(\"data_source\")}')
    # 应该显示: eastmoney_api 而不是 fallback_mock

asyncio.run(test())
"
```

## 为什么之前能成功?

您提到"前面市场热度我们获取过真实的数据",可能的原因:

1. **之前没有开启代理软件**
2. **之前的代理配置包含了东方财富的直连规则**
3. **代理软件更新后规则被重置**

## 代码修改记录

已完成的优化(虽然没解决网络问题):

1. ✅ 使用`ak.stock_zh_a_spot`替代`ak.stock_zh_a_spot_em`
2. ✅ 添加完整HTTP headers(基于成功案例)
3. ✅ 移除时间戳参数`_`(避免缓存问题)
4. ✅ 删除缓存机制(按您要求)

这些优化在网络正常后会提高稳定性。

## 下一步行动

**请按以下顺序操作:**

1. 检查是否运行了代理软件(ClashX/Surge/Shadowrocket)
2. 如有,添加东方财富直连规则
3. 重启代理软件
4. 运行上述验证命令
5. 如果成功,重启后端服务

如果以上步骤都无效,请告知:
- 您使用的代理软件名称
- 或者是否愿意尝试完全关闭代理软件测试
