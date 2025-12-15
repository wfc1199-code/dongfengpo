# 东风破项目 - 版本管理完成版

## 📊 当前版本信息
- **版本标识**: v2.0-data-pipeline-refactor
- **创建时间**: 2025-09-11 09:30:00
- **状态**: 🚧 分时数据处理中心重构进行中（核心链路已联通，前端整合中）
- **版本快照**: v20250911_093000
- **新增能力**: 多服务拆分、数据流水线联通、策略引擎、机会聚合、风险提示、统一文档与脚本

## 🔧 系统配置

### 端口配置
- **前端端口**: 3000 (React开发服务器)
- **后端端口**: 9000 (FastAPI服务)
- **记忆口诀**: 东风破=3000，clean_quant=3600

### 启动脚本
```bash
# 启动完整数据流水线（需Redis与依赖）
./scripts/start_pipeline.sh

# Legacy 前后端
./scripts/start_dongfeng.sh
./scripts/stop_dongfeng.sh
```

## ⚡ 性能优化配置

### 刷新频率设置（已优化）
- **App主程序**: 15秒间隔（默认）
- **异动检测**: 12秒间隔
- **交易系统**: 20秒间隔
- **用户可选**: 5秒/10秒/15秒/30秒/60秒

### 已解决的问题
1. ✅ 后端依赖包安装完成
2. ✅ 分时刷新性能优化
3. ✅ 多组件频繁刷新问题解决
4. ✅ 用户可配置刷新间隔

## 🚀 功能状态

### 已完成（v2.0 数据流水线）
- ✅ Collector Gateway：多源行情采集 → `dfp:raw_ticks`
- ✅ Stream Buffer：Stream 复制、备份
- ✅ Data Cleaner：Tick 清洗、标准化输出
- ✅ Data Lake Writer：历史数据落地（Parquet/CSV）
- ✅ Feature Pipeline：多窗口特征计算并发布
- ✅ Strategy Engine：插件化策略执行（RapidRise）
- ✅ Opportunity Aggregator：机会生命周期、频道推送
- ✅ Risk Guard：风险告警频道
- ✅ Signal API：REST 查询 + 健康检查
- ✅ Signal Streamer：WebSocket 实时推送
- ✅ Backtest Service：策略回测接口

### 进行中 / 待办
- 🔄 前端 UI 与新服务联动、实时面板改造
- 🔄 更丰富的策略与风险规则
- 🔄 端到端集成测试 & CI/CD 流程
- 🔄 容器化/部署脚本更新

## 📁 关键文件

### 数据流水线服务
- `services/collector-gateway/`
- `services/stream-buffer/`
- `services/data-cleaner/`
- `services/data-lake-writer/`
- `services/feature-pipeline/`
- `services/strategy-engine/`
- `services/opportunity-aggregator/`
- `services/risk-guard/`
- `services/signal-api/`
- `services/signal-streamer/`
- `services/backtest-service/`

### 支撑文档与脚本
- `docs/分时数据处理中心服务总览.md`
- `docs/分时数据处理中心启动指南.md`
- `docs/分时数据处理中心环境变量.md`
- `docs/测试策略.md`
- `scripts/start_pipeline.sh`
- `.env.example`

## 🔧 依赖环境

### Python依赖
- 详见各服务 `services/*/requirements.txt`
- 根目录 `.env.example` 提供统一变量模板

### Node.js依赖
- React 18+
- TypeScript
- ECharts图表库

## ⚠️ 已知问题
- 无重大已知问题
- 所有核心功能正常运行

## 🛟 回退说明
如果新开发出现问题，可以：
1. `git checkout stable-v1.0` - 回退到此稳定版本
2. 使用物理备份恢复
3. 重新运行启动脚本

## 📝 更新记录
- 2025-01-28: 创建首个稳定版本标记
- 2025-01-28: 完成性能优化
- 2025-01-28: 建立版本控制体系
- 2025-08-05: 完成版本管理模块
  - ✅ 创建完整版本管理系统
  - ✅ 实现版本时间轴界面
  - ✅ 添加自动快照功能
  - ✅ 集成变更追踪机制
  - ✅ 优化K线图缓存性能
- **2025-09-11: 启动分时数据处理中心重构**
  - ✅ 拆分采集/清洗/特征/策略/聚合/风险等服务
  - ✅ 新增 REST & WebSocket 接口、回测服务
  - ✅ 发布服务总览、启动指南、环境变量、测试策略文档
  - 🔄 待完成：前端整合、CI/CD、部署自动化

## 🗂️ 版本历史
### v20250805_071058 - 性能优化版本
- K线图性能优化，数据缓存机制（5分钟有效期）
- 错误处理改进，非交易时间检测
- 请求管理优化，竞态条件防护
- API响应提速，降至30ms间隔

### v20250805_071349 - 版本管理完成版
- 完整版本管理系统实现
- 版本时间轴界面开发
- 自动快照创建和存储
- 变更记录追踪功能
- 版本统计分析面板

### v20250911_093000 - 数据流水线重构 ⭐当前版本⭐
- 新的数据采集→清洗→特征→策略→机会全链路上线
- 风险提示、回测、REST/WS 接口服务化
- 补充环境配置、启动脚本、测试策略文档
- 前端整合、CI/CD、部署自动化仍在进行中
