# Source Tree Analysis

```
project-root/
├─ frontend/               # React + Vite + Ant Design + zustand + echarts
│  ├─ src/
│  │  ├─ components/
│  │  ├─ pages/
│  │  ├─ api/              # axios/http helpers
│  │  ├─ store/            # state (zustand)
│  │  └─ styles/
│  ├─ public/
│  └─ vite.config.ts
├─ services/               # Python microservices (FastAPI)
│  ├─ api-gateway/
│  ├─ signal-api/          # business APIs (stocks/signals/opportunities/anomaly/limit-up/config)
│  ├─ strategy-engine/     # strategy execution
│  ├─ signal-streamer/     # websocket push
│  ├─ opportunity-aggregator/
│  ├─ collector-gateway/
│  ├─ stream-buffer/
│  ├─ risk-guard/
│  ├─ feature-pipeline/
│  ├─ data-cleaner/
│  ├─ data-lake-writer/
│  ├─ backtest-service/
│  └─ unified-gateway/
├─ libs/
│  ├─ strategy-sdk/        # shared strategy helpers (Python)
│  └─ data_contracts/      # JSON/Pydantic contracts
├─ docs/                   # generated + existing documentation
├─ static/                 # static assets
├─ scripts/                # utility scripts
├─ tests/                  # assorted test/HTML fixtures
├─ trading_opportunity_hub.html and other HTML tools
└─ docker-compose.yml      # service orchestration
```

Notes:
- Each service has `requirements.txt` / `requirements-dev.txt`.
- Frontend uses Vite; scripts include `start/build/serve/test`.
- Multiple standalone HTML tools remain at repo root.


