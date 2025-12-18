# 东风破 - 智能股票量化交易系统

[![CI](https://github.com/wfc1199-code/dongfengpo/workflows/CI/badge.svg)](https://github.com/wfc1199-code/dongfengpo/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> 实时、智能、可靠的股票量化交易平台

---

## 📚 核心文档导航 ⭐

**开发工作请先阅读以下文档**：

### 必读文档

1. 📄 **[核心文档索引](./docs/核心文档索引.md)** ← **从这里开始！**
2. 📄 [PRD - 产品需求文档](./docs/analysis/PRD-东风破-股票量化交易系统.md)
3. 📐 [量化策略开发闭环设计](./docs/量化策略开发闭环设计.md)
4. 📐 [开发流程规范](./docs/开发流程规范.md)

### 开发指南

- 📖 [Git 工作流指南](./docs/GIT_WORKFLOW.md)
- 📖 [Commit Message 规范](./docs/COMMIT_MESSAGE_GUIDE.md)
- 📋 [PR 模板](./.github/PULL_REQUEST_TEMPLATE.md)

---

## ⚡ 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- Redis 7.0+

### 安装依赖

```bash
# 后端
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 运行服务

```bash
# 启动所有服务（推荐）
./start_all.sh

# 或分别启动
# 1. Signal API
cd services/signal-api
python -m uvicorn signal_api.main:app --port 9001 --reload

# 2. API Gateway
cd services/api-gateway
python -m uvicorn api_gateway.main:app --port 8080 --reload

# 3. 前端
cd frontend
npm run dev
```

访问：http://localhost:3000

---

## 🏗️ 项目架构

```
东风破/
├── services/                    # 后端微服务
│   ├── signal-api/             # 信号服务（核心）
│   ├── api-gateway/            # API网关
│   └── backtest-engine/        # 回测引擎（规划中）
├── shared/                     # 共享模块（规划中）
│   ├── strategies/             # 策略库
│   ├── indicators/             # 技术指标
│   └── models/                 # 数据模型
├── frontend/                   # 前端应用
├── docs/                       # 文档
│   ├── 核心文档索引.md         # ⭐ 文档导航
│   └── analysis/               # PRD等分析文档
└── tests/                      # 测试
```

---

## 🎯 核心功能

- ✅ **实时行情监控**：毫秒级数据更新
- ✅ **异动检测**：急速拉升、放量突破、大单买入
- ✅ **涨停预测**：AI 驱动的涨停预测
- ✅ **盯盘雷达**：实时扫描市场异动
- ✅ **明日潜力**：收盘后预测次日潜力股
- ⏳ **回测系统**：策略回测和性能分析（开发中）
- ⏳ **参数优化**：遗传算法参数优化（开发中）

---

## 🛠️ 技术栈

**后端**：

- FastAPI - Web 框架
- Pandas/NumPy - 数据处理
- AkShare/TuShare - 数据源
- Redis - 缓存
- PostgreSQL - 数据库

**前端**：

- React 18 + Vite
- Ant Design
- ECharts
- WebSocket

**DevOps**：

- Docker
- GitHub Actions
- Pytest/Jest

---

## 📊 开发进度

查看 [项目看板](https://github.com/wfc1199-code/dongfengpo/projects) 了解最新进度

**当前 Sprint**: Phase 2 - 回测与参数优化系统

---

## 🤝 贡献指南

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 遵守 [开发流程规范](./docs/开发流程规范.md)
4. 提交代码 (`git commit -m 'feat: Add some AmazingFeature'`)
5. 推送到分支 (`git push origin feature/AmazingFeature`)
6. 创建 Pull Request

**重要**：

- ✅ 遵守 Conventional Commits 规范
- ✅ 确保所有测试通过
- ✅ 测试覆盖率 >= 80%
- ✅ 通过代码审查

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 📞 联系方式

- 项目地址：[GitHub](https://github.com/wfc1199-code/dongfengpo)
- 问题反馈：[Issues](https://github.com/wfc1199-code/dongfengpo/issues)

---

**⚠️ 免责声明**

本系统提供的所有信息和数据仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。用户应根据自身情况独立做出投资决策，并自行承担投资风险。
