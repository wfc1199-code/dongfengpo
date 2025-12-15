# 前端组件切换性能优化方案

## 🔍 问题诊断

### 当前问题
组件切换时加载很慢，影响用户体验：
- 今日预测
- 连板监控  
- 自选股
- 市场扫描
- 二板候选
- 机会流
- 板块热度

### 根本原因

#### 1. **组件重新挂载导致状态丢失**
```typescript
// 当前实现 (App.tsx)
const renderActiveSection = () => {
  const section = monitoringSections.find((s) => s.id === activeTab);
  return section.render({ onStockSelect, stocks, anomalies });
}

// ❌ 问题：只渲染当前激活的标签
// 切换标签时，之前的组件被卸载，新组件重新挂载
```

#### 2. **每次挂载都重新加载数据**
```typescript
// TimeLayeredLimitUpTracker.tsx
useEffect(() => {
  fetchLimitUpData(); // ❌ 每次挂载都执行
}, [fetchLimitUpData]);
```

#### 3. **没有数据缓存机制**
- API 请求没有缓存
- 切换回之前的标签时，需要重新请求数据
- 网络延迟累积

#### 4. **懒加载的副作用**
- React.lazy 虽然减少初始包大小
- 但首次切换时需要下载组件代码
- 下载 + 解析 + 执行 + 数据加载 = 明显延迟

## 🚀 优化方案

### 方案一：保持组件挂载（推荐）⭐

**核心思路**：使用 CSS `display` 控制显示/隐藏，而不是条件渲染

#### 实现代码

```typescript
// App.tsx - 优化后
const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<MonitoringTabId>('limitup');
  
  return (
    <div className="app">
      <div className="left-panel">
        {/* 导航 */}
        <div className="left-panel-nav">
          {monitoringSections.map((section) => (
            <button
              key={section.id}
              className={`nav-item ${activeTab === section.id ? 'active' : ''}`}
              onClick={() => setActiveTab(section.id)}
            >
              {section.title}
            </button>
          ))}
        </div>

        {/* 内容区 - 所有组件都保持挂载 */}
        <div className="left-panel-body">
          {monitoringSections.map((section) => (
            <div
              key={section.id}
              className="section-container"
              style={{ display: activeTab === section.id ? 'block' : 'none' }}
            >
              {section.render({ onStockSelect, stocks, anomalies })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
```

#### 优点
- ✅ 组件状态保持
- ✅ 数据不需要重新加载
- ✅ 切换瞬时完成
- ✅ 改动最小，风险低

#### 缺点
- ⚠️ 初始渲染所有组件，首次加载稍慢
- ⚠️ 内存占用略高

### 方案二：全局数据缓存层

**核心思路**：使用 SWR 或 React Query 管理数据请求和缓存

#### 安装依赖

```bash
npm install swr
# 或
npm install @tanstack/react-query
```

#### 使用 SWR 实现

```typescript
// hooks/useLimitUpData.ts
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then(res => res.json());

export const useLimitUpData = () => {
  const { data, error, isLoading, mutate } = useSWR(
    'http://localhost:9000/api/limit-up/predictions?limit=100',
    fetcher,
    {
      refreshInterval: 60000, // 60秒自动刷新
      revalidateOnFocus: false, // 窗口聚焦时不重新验证
      dedupingInterval: 10000, // 10秒内不重复请求
    }
  );

  return {
    limitUpStocks: data?.predictions || [],
    isLoading,
    error,
    refresh: mutate,
  };
};

// TimeLayeredLimitUpTracker.tsx - 优化后
const TimeLayeredLimitUpTracker: React.FC<Props> = ({ onStockSelect }) => {
  const { limitUpStocks, isLoading, refresh } = useLimitUpData();
  // ✅ 数据自动缓存，切换回来时立即显示
  
  // 移除手动的 fetch 逻辑
  // ❌ const [data, setData] = useState([]);
  // ❌ useEffect(() => { fetch... }, []);
  
  return (
    <div>
      {isLoading ? <LoadingSpinner /> : <StockList stocks={limitUpStocks} />}
    </div>
  );
};
```

#### 优点
- ✅ 自动缓存和重验证
- ✅ 自动去重请求
- ✅ 自动后台刷新
- ✅ 内置加载和错误状态

#### 缺点
- ⚠️ 需要重构所有数据请求逻辑
- ⚠️ 增加依赖包

### 方案三：预加载策略

**核心思路**：鼠标悬停时预加载组件和数据

```typescript
// hooks/usePrefetch.ts
import { prefetch } from 'swr';

export const usePrefetch = () => {
  const prefetchData = useCallback((url: string) => {
    prefetch(url, fetcher);
  }, []);

  return { prefetchData };
};

// App.tsx
const App: React.FC = () => {
  const { prefetchData } = usePrefetch();
  
  return (
    <div className="left-panel-nav">
      {monitoringSections.map((section) => (
        <button
          key={section.id}
          onMouseEnter={() => {
            // 鼠标悬停时预加载数据
            if (section.apiUrl) {
              prefetchData(section.apiUrl);
            }
          }}
        >
          {section.title}
        </button>
      ))}
    </div>
  );
};
```

### 方案四：骨架屏优化

**核心思路**：用骨架屏替代空白loading，提升感知性能

```typescript
// components/SkeletonLoader.tsx
export const StockListSkeleton = () => (
  <div className="skeleton-container">
    {[1, 2, 3, 4, 5].map(i => (
      <div key={i} className="skeleton-item">
        <div className="skeleton-line skeleton-title"></div>
        <div className="skeleton-line skeleton-text"></div>
      </div>
    ))}
  </div>
);

// CSS
.skeleton-line {
  height: 16px;
  background: linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 50%, #2a2a2a 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  border-radius: 4px;
}

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

## 📊 性能对比

| 方案 | 首次加载 | 切换速度 | 内存占用 | 实现难度 | 推荐指数 |
|------|---------|---------|---------|---------|---------|
| 当前实现 | 快 | 慢 (2-3秒) | 低 | - | ⭐ |
| 方案一：保持挂载 | 中 | 极快 (<50ms) | 中 | 低 | ⭐⭐⭐⭐⭐ |
| 方案二：SWR缓存 | 快 | 快 (<200ms) | 低 | 中 | ⭐⭐⭐⭐ |
| 方案三：预加载 | 快 | 中 | 低 | 中 | ⭐⭐⭐ |
| 方案四：骨架屏 | 快 | 感知快 | 低 | 低 | ⭐⭐⭐ |

## 🎯 推荐实施步骤

### 第一阶段：快速优化（30分钟）
1. ✅ 实施方案一：修改 App.tsx，保持所有组件挂载
2. ✅ 添加简单骨架屏（方案四）

### 第二阶段：深度优化（2小时）
3. ✅ 为关键组件添加 React.memo
4. ✅ 检查并优化不必要的 re-render
5. ✅ 添加预加载逻辑（方案三）

### 第三阶段：架构升级（1天）
6. ✅ 引入 SWR 或 React Query（方案二）
7. ✅ 重构所有数据请求逻辑
8. ✅ 添加全局错误处理和重试机制

## 📝 代码示例

完整的优化代码请参考：
- [优化后的 App.tsx](#app-tsx-优化版)
- [SWR 数据缓存 Hook](#swr-hooks)
- [骨架屏组件](#skeleton-components)

## ⚠️ 注意事项

1. **内存管理**：保持所有组件挂载会增加内存占用，需要监控
2. **初始加载**：首次加载时间会增加，可通过懒加载优化
3. **数据同步**：多个组件同时活跃时，注意数据一致性
4. **清理逻辑**：组件的 cleanup 逻辑（useEffect return）仍然重要

## 🔧 监控指标

优化后需要监控：
- Time to Interactive (TTI)
- First Contentful Paint (FCP)
- 标签切换响应时间
- 内存占用
- 网络请求数量

## 📈 预期效果

- 标签切换时间：从 2-3秒 → <50ms
- 用户感知：从"卡顿、等待" → "流畅、即时"
- 数据请求：减少 70% 的重复请求
- 开发体验：更容易维护和扩展
