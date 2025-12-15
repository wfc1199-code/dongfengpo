+# data-contracts
+
+共享数据契约定义，基于 Pydantic 构建，供分时数据处理中心的各服务复用。
+
+## 包含模型
+
+- `TickRecord` / `CleanedTick`：采集端与清洗端的行情记录
+- `FeatureSnapshot`：多窗口特征快照
+- `StrategySignal` / `OpportunitySignal` / `OpportunityState`：策略输出与机会生命周期
+- `RiskAlert` / `RiskSeverity`：风控告警结构
+
+## 使用方式
+
+```bash
+# 在任一服务目录执行（建议已激活虚拟环境）
+pip install -e ../../libs/data_contracts
+```
+
+安装后可直接 `from data_contracts import ...` 统一复用模型。
+`pyproject.toml` 已声明核心依赖，CI 或部署流程也可通过 `pip install libs/data_contracts` 完成本地包安装。
+
+> 后续可配合 `model_json_schema()` 生成 JSON Schema / OpenAPI，用于前后端或跨服务契约同步。
