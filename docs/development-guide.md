# Development Guide (Initial)

## Prerequisites
- Python 3.x for services; Node 18+ for frontend
- Install per-service deps: `pip install -r requirements.txt` (and `requirements-dev.txt` if needed)
- Frontend: `npm install` (Vite/React)

## Run (indicative)
- Signal API (example): `uvicorn signal_api.app:app --reload --port 9001`
- API Gateway: `uvicorn main:app --reload --port 8080` (path services/api-gateway)
- Signal Streamer: `uvicorn signal_streamer.server:app --reload --port 8002`
- Strategy Engine: (implementation-specific; check service entry)
- Frontend: `npm run start` (Vite dev), `npm run build` for production
- Docker compose: `docker-compose up` (review compose for service names/ports)

## Testing (partial)
- Frontend: `npm run test`
- Python services: run pytest if present (tests/), or targeted module tests

## Env/Config
- Config/JSON used by signal-api: `backend/data/config.json`, `backend/data/stock_snapshot.json`
- Ports (from earlier analysis): gateway 8080, signal-api 9001, strategy-engine 8003, signal-streamer 8002

_More detailed per-service run/test/deploy steps to be generated with deeper scan._

