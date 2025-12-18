# 架构方案：AI量化分析平台 - v20 完整版

## 1. 架构演进对比 (Architecture Evolution)

### 1.1 现有架构 (Current / Legacy)
目前的架构是简单的"直连查询"模式，无状态、无风控、无回测。

```mermaid
graph LR
    subgraph Frontend [东风破前端]
        LegacyP["盯盘雷达页面"]
    end

    subgraph Backend [Signal API 服务]
        Router["limit_up.py"]
    end

    subgraph Data [数据源]
        AkShare["AkShare API"]
    end

    LegacyP -->|HTTP| Router
    Router -->|Direct Call| AkShare
    AkShare -->|JSON| Router
    Router -->|JSON| LegacyP
```

### 1.2 集成后架构 (Integrated / Target)
采用 **"旁路挂载 (Sidecar)"** 模式。新旧系统平行运行。

```mermaid
graph TD
    subgraph Frontend [前端 Dashboard]
        LegacyP[旧: 盯盘雷达]
        QuantP["新: AI 量化实验室"]
    end

    subgraph Backend [Signal API 服务]
        subgraph LegacyModule [Legacy Module]
            OldRouter[limit_up.py]
        end
        
        subgraph QuantModule [Quant Module]
            NewRouter[quant.py]
            RT["Realtime Engine"]
            BT["Backtest Engine"]
            Risk["Risk Manager"]
            DataLayer["Data Layer"]
        end
    end

    subgraph Storage [本地数据湖]
        DuckDB[("DuckDB + Parquet")]
        MetaDB[("SQLite")]
    end

    subgraph External [外部数据源]
        Tushare["Tushare Pro"]
        AkShare["AkShare"]
        DeepSeek["DeepSeek AI"]
    end

    LegacyP --> OldRouter --> AkShare
    QuantP --> NewRouter --> RT & BT
    RT --> Risk --> AkShare & DeepSeek
    BT --> DuckDB
    Tushare -->|每日增量| DataLayer --> DuckDB
```

---

## 2. 核心数据流图 (Core Data Flow)

### 2.1 潜伏策略工作流 (Ambush Workflow)

```mermaid
sequenceDiagram
    participant Cron as 定时任务
    participant TS as Tushare Client
    participant Duck as DuckDB
    participant Quant as Quant Engine
    participant AI as DeepSeek Agent
    participant DB as SQLite

    Cron->>TS: 1. 下载分钟线 & 资金流
    TS->>Duck: 2. 存入 Parquet
    Cron->>Quant: 3. 触发扫描
    Quant->>Duck: 4. 读取 30天数据
    Quant->>Quant: 5. 计算因子
    Quant->>AI: 6. AI 分析 Top 50
    AI-->>Quant: 7. 返回 Top 5
    Quant->>DB: 8. 保存明日池
```

### 2.2 点火策略工作流 (Ignition Workflow)

```mermaid
sequenceDiagram
    participant User as 前端
    participant RT as Realtime Engine
    participant Risk as Risk Manager
    participant Ak as AkShare

    loop Every 3 Seconds
        RT->>Ak: 1. 获取快照
        RT->>RT: 2. 匹配信号
        opt 触发信号
            RT->>Risk: 3. 风控检查
            alt Pass
                RT->>User: 4. 推送信号
            else Reject
                RT->>User: 4. 推送拦截
            end
        end
    end
```

---

## 3. 核心改进 (From Expert Review)

### P0: 数据一致性
*   **断点续传**: 记录 `checkpoint`，自动补录。
*   **完整性校验**: 每日必须满 240 根 K 线。
*   **备份策略**: 每日备份 Parquet 到 `backup/`。

### P0: 风控规则
| 规则 | 阈值 | 动作 |
|------|------|------|
| 单笔止损 | 亏损 > 3% | 立即平仓 |
| 单日熔断 | 回撤 > 5% | 停止开仓 |
| 单票持仓 | > 20% | 禁止加仓 |
| 同板块 | > 3 只 | 禁止买入 |

### P1: 可观测性
*   **SLA**: 信号延迟 < 5秒。
*   **告警**: 延迟超标亮黄灯。

---

## 4. 实施路线图

### Phase 1: 基础设施 (P0)
- [ ] 搭建 DuckDB + 校验器 + 断点续传
- [ ] 实现风控规则表

### Phase 2: 回测 (P1)
- [ ] Bar-by-Bar 回测引擎
- [ ] 样本外验证

### Phase 3: 实盘 (P2)
- [ ] 仿真模式
- [ ] AI 审计日志
