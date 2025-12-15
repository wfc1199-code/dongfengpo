# 网络连接问题诊断报告

## 问题描述

市场扫描器和板块热度模块都返回模拟数据,而非真实数据。

## 根本原因

东方财富API(push2.eastmoney.com)在当前macOS网络环境下**无法连接**:

```
错误: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

## 测试结果

| 数据源 | 接口 | 状态 |
|-------|------|------|
| 东方财富push2 | `http://push2.eastmoney.com/api/qt/clist/get` | ❌ 连接失败 |
| 新浪财经 | `ak.stock_zh_a_spot()` | ✅ 直接调用成功<br>❌ 服务环境失败 |
| 东财涨停池 | `ak.stock_zt_pool_em(date='20251003')` | ✅ 成功获取52条数据 |

## 网络层测试

```bash
$ curl "http://push2.eastmoney.com/api/qt/clist/get?..."
* Connected to push2.eastmoney.com (198.18.0.12) port 80
* Request completely sent off
* Empty reply from server  # 服务器返回空响应
curl: (52) Empty reply from server
```

**发现**: 能DNS解析,能TCP连接,但HTTP请求返回空响应。

## 可能原因

1. **代理/VPN设置**: 198.18.0.12 是典型的代理/VPN分配的IP地址
2. **防火墙规则**: macOS防火墙可能阻止了特定API请求
3. **反爬虫机制**: 东方财富检测到异常请求模式

## 解决方案

### 方案1: 检查网络代理设置

```bash
# 检查当前HTTP代理
echo $HTTP_PROXY
echo $HTTPS_PROXY
echo $NO_PROXY

# 查看系统代理
scutil --proxy

# 临时禁用代理测试
unset HTTP_PROXY
unset HTTPS_PROXY
```

### 方案2: 添加东方财富域名到代理白名单

如果使用ClashX/Surge等代理工具,添加规则:
```
DOMAIN-SUFFIX,eastmoney.com,DIRECT
DOMAIN,push2.eastmoney.com,DIRECT
```

### 方案3: 使用备用数据源

已实现但效果有限:
- ✅ 新浪财经作为备份(但在服务环境下也失败)
- ✅ 使用涨停池数据计算板块热度(成功但数据量有限)

### 方案4: 修改请求策略 (推荐尝试)

1. **增加请求头伪装**:
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Referer': 'http://quote.eastmoney.com/center/gridlist.html',
    'Connection': 'keep-alive',
    'Host': 'push2.eastmoney.com'
}
```

2. **增加重试和延迟**:
```python
import time
import random

for i in range(3):
    time.sleep(random.uniform(1, 3))  # 随机延迟1-3秒
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            break
    except:
        continue
```

## 当前代码状态

### 已完成的修改

1. ✅ 删除缓存机制代码(按用户要求)
2. ✅ 替换`ak.stock_zh_a_spot_em` → `ak.stock_zh_a_spot`(使用更稳定接口)
3. ✅ 添加新浪财经作为备份数据源(但服务环境下仍失败)

### 还需要做的

1. 解决网络连接问题(push2.eastmoney.com)
2. 或者寻找完全不依赖东财API的替代方案

## 建议

**优先级1**: 检查并修复网络代理配置,因为之前能够成功获取数据,说明问题可能在近期网络环境变化

**优先级2**: 如果网络无法修复,需要重构数据源策略,完全依赖可用的接口(如涨停池+其他东财可用接口)

## 用户之前的提示

> "前面市场热度我们获取过真实的数据,当时我还提醒过上网搜索成功的解决方案"

这表明:
1. 之前这些API能正常工作
2. 可能有特定的网络配置或请求技巧使其工作
3. 需要找回之前的成功方案
