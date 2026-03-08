# Course Prereq Planner

React frontend with a thin FastAPI adapter that reuses existing Python planner and LLM modules.

## Features

- Deterministic prerequisite/graduation feasibility planning
- Alternate outcomes for infeasible deadlines
- Azure LLM track recommendation + final natural language plan
- Deterministic fallback if Azure is unavailable
- Route graph modal for selected feasible path

## Architecture

- `frontend/` (React + TypeScript)
- `backend/` (FastAPI adapter endpoints only)
- Existing logic reused as-is:
  - `planner_engine.py`
  - `track_recommender.py`
  - `azure_llm_client.py`

## Setup

1) Activate Python environment and install backend dependencies:

```bash
source ".env/bin/activate"
pip install -r requirements.txt
```

2) Install frontend dependencies:

```bash
cd frontend
npm install
cd ..
```

## Azure Configuration

Create `.env.local` in repo root:

```bash
AZURE_OPENAI_ENDPOINT="https://<your-resource>.services.ai.azure.com"
AZURE_OPENAI_API_KEY="<your-api-key>"
AZURE_OPENAI_API_VERSION="2024-06-01"
AZURE_OPENAI_DEPLOYMENT="<your-deployment-name>"
```

Load env vars before running backend:

```bash
set -a
source .env.local
set +a
```

## Run (React + FastAPI)

1) Start backend API:

```bash
source ".env/bin/activate"
uvicorn backend.main:app --reload --port 8000
```

2) Start React UI in another terminal:

```bash
cd frontend
npm run dev
```

Frontend defaults to `http://localhost:5173` and API to `http://localhost:8000`.

## API Endpoints

- `GET /health`
- `GET /courses`
- `POST /plan/generate`
- `POST /tracks/recommend`
- `POST /tracks/finalize`
- `POST /graph/route`

## Legacy Streamlit UI

Old Streamlit interface is still available:

```bash
streamlit run pied_piper_planner.py
```

## Tests

```bash
pytest -q
```

Frontend build validation:

```bash
cd frontend
npm run build
```
