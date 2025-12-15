# data-lake-writer

历史数据落地与归档服务：
- 消费 `dfp:clean_ticks` Stream，将批量数据写入本地数据湖目录。
- 支持 Parquet/CSV 两种输出格式，可按环境变量定制。
- 后续可扩展上传至对象存储或 ClickHouse。

## 配置

环境变量前缀 `LAKE_WRITER_`：

- `REDIS_URL`：Redis 连接串 (默认 `redis://localhost:6379/0`)
- `INPUT_STREAM`：消费 Stream 名称 (默认 `dfp:clean_ticks`)
- `OUTPUT_DIR`：输出目录 (默认 `data-lake`)
- `FILE_FORMAT`：`parquet` 或 `csv`
- `MAX_BUFFER_SIZE`：达到阈值即触发强制落地
- `FLUSH_INTERVAL_SECONDS`：定时落地间隔

## 运行

```bash
pip install -r requirements.txt
python -m data_lake_writer.main
```

## 开发与测试

```bash
pip install -r requirements-dev.txt
pytest services/data-lake-writer/tests
```
