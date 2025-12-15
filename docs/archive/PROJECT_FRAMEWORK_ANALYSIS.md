# 东风破系统 - 项目框架分析报告

## 一、项目概述

**项目名称**: 东风破 - AI异动拉升检测系统  
**版本**: v1.0.0  
**平台**: macOS  
**目标**: 专为股票市场异动检测和分析而设计的全栈应用系统

## 二、技术架构

### 2.1 前端技术栈

| 技术 | 版本 | 用途 |
|-----|------|------|
| React | 19.1.0 | 前端框架 |
| TypeScript | 4.9.5 | 类型安全 |
| ECharts | 5.6.0 | 数据可视化图表 |
| Zustand | 5.0.5 | 状态管理 |
| React Scripts | 5.0.1 | 构建工具 |

**端口配置**: 3000

### 2.2 后端技术栈

| 技术 | 版本 | 用途 |
|-----|------|------|
| FastAPI | 0.104.1 | Web框架 |
| Uvicorn | 0.24.0 | ASGI服务器 |
| Pandas | ≥2.0 | 数据处理 |
| NumPy | ≥1.24 | 数值计算 |
| Redis | 5.0.1 | 缓存系统 |
| SQLAlchemy | 2.0.23 | ORM框架 |
| Pydantic | 2.11.7 | 数据验证 |
| Scikit-learn | ≥1.3.0 | 机器学习 |
| WebSockets | 12.0 | 实时通信 |

**端口配置**: 9000

## 三、项目结构

### 3.1 目录组织

```
东风破/
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/    # React组件
│   │   ├── hooks/         # 自定义Hook
│   │   ├── services/      # API服务
│   │   ├── types/         # TypeScript类型
│   │   └── utils/         # 工具函数
│   └── public/            # 静态资源
│
├── backend/               # 后端服务
│   ├── api/              # API路由
│   ├── core/             # 核心业务逻辑
│   ├── data/             # 数据配置
│   └── versions/         # 版本管理
│
├── scripts/              # 运维脚本
├── logs/                 # 日志文件
├── config/               # 配置文件
└── docs/                 # 项目文档
```

### 3.2 核心模块

#### 后端核心模块 (`backend/core/`)
- **anomaly_detection.py**: 异动检测引擎
- **anomaly_analyzer.py**: 异动分析器
- **data_sources.py**: 数据源管理
- **limit_up_predictor.py**: 涨停预测器
- **market_behavior_analyzer.py**: 市场行为分析
- **support_resistance/**: 支撑阻力分析模块
  - dynamic_sr.py: 动态支撑阻力
  - multi_timeframe.py: 多时间框架分析
  - strength_rating.py: 强度评级
  - volume_profile.py: 成交量分布
- **cache_manager.py**: 缓存管理
- **config.py**: 配置管理
- **monitoring.py**: 系统监控
- **security.py**: 安全中间件
- **version_manager.py**: 版本控制

#### API路由模块 (`backend/api/`)
- **anomaly_routes.py**: 异动检测API
- **limit_up_routes.py**: 涨停板分析API
- **market_behavior_routes.py**: 主力行为分析API
- **market_scanner.py**: 全市场扫描API
- **support_resistance_tdx.py**: 支撑阻力API (通达信风格)
- **transaction_routes.py**: 交易数据API
- **price_alert_routes.py**: 价格预警API
- **version_routes.py**: 版本管理API

## 四、功能架构

### 4.1 核心功能

1. **异动检测系统**
   - 实时监控股票异动
   - 多维度异动分析
   - 智能预警机制

2. **技术分析系统**
   - 支撑阻力位计算
   - 多时间框架分析
   - 成交量分布分析

3. **市场行为分析**
   - 主力资金流向
   - 板块热度分析
   - 涨停板预测

4. **数据管理系统**
   - 实时数据采集
   - 缓存优化
   - 历史数据存储

### 4.2 前端组件架构

#### 核心展示组件
- **StockChart**: 股票K线图表
- **TimeShareChartFixed**: 分时图
- **AnomalyPanel**: 异动面板
- **MarketBehaviorPanel**: 市场行为面板
- **SupportResistance**: 支撑阻力可视化

#### 分析组件
- **AnomalyAnalysisPanel**: 异动分析面板
- **TransactionAnalysisPanel**: 交易分析面板
- **SectorAnalysis**: 板块分析
- **HotSectors**: 热门板块

#### 管理组件
- **ManagementDashboard**: 管理仪表板
- **VersionManager**: 版本管理器
- **MonitoringScope**: 监控范围配置

## 五、系统特性

### 5.1 性能优化
- **并行处理**: 使用异步和并发提高数据处理效率
- **缓存策略**: Redis缓存减少重复计算
- **懒加载**: 前端组件按需加载
- **资源管理**: 自动清理和资源回收

### 5.2 安全机制
- **CORS配置**: 跨域资源共享控制
- **请求限流**: 防止API滥用
- **输入验证**: Pydantic数据验证
- **JWT认证**: 用户身份验证

### 5.3 监控与维护
- **日志系统**: 分级日志记录
- **性能监控**: Prometheus指标
- **健康检查**: 服务健康状态监测
- **版本管理**: 自动备份和版本控制

## 六、部署架构

### 6.1 启动流程
1. Python虚拟环境初始化
2. 依赖包安装检查
3. 后端服务启动 (端口9000)
4. 前端服务启动 (端口3000)
5. 健康检查验证

### 6.2 运维脚本
- **start_dongfeng.sh**: 系统启动脚本
- **stop_dongfeng.sh**: 系统停止脚本
- **health_check.sh**: 健康检查脚本
- **restore_stable.sh**: 稳定版本恢复

## 七、开发规范

### 7.1 代码组织
- 模块化设计，功能解耦
- TypeScript类型安全
- 统一的错误处理机制
- 完善的注释和文档

### 7.2 数据流
```
用户界面 (React)
    ↓↑
API服务层 (FastAPI)
    ↓↑
业务逻辑层 (Core Modules)
    ↓↑
数据访问层 (Data Sources)
    ↓↑
外部数据源 / 缓存系统
```

## 八、系统优势

1. **全栈架构**: 前后端分离，技术栈现代化
2. **高性能**: 异步处理、缓存优化、并行计算
3. **可扩展**: 模块化设计，易于功能扩展
4. **实时性**: WebSocket支持，实时数据推送
5. **可维护**: 完善的日志、监控和版本管理

## 九、后续优化建议

1. **微服务化**: 将核心功能拆分为独立服务
2. **容器化部署**: 使用Docker简化部署流程
3. **数据库优化**: 引入时序数据库优化历史数据存储
4. **AI增强**: 集成更多机器学习模型提升预测准确性
5. **测试覆盖**: 增加单元测试和集成测试

---

*生成时间: 2025-08-09*  
*系统版本: v1.0.0*