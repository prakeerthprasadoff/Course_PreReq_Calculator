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

## Deploy on Hugging Face Spaces (Docker)

This repo includes a root `Dockerfile` that:
- builds `frontend/` with Vite
- serves the built React app from FastAPI
- runs a single process on port `7860` (Spaces default)

### Steps

1) Create a **new Hugging Face Space** with **SDK = Docker**.
2) Push this repository to that Space.
3) In Space **Settings -> Variables and secrets**, add:
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_API_KEY` (Secret)
   - `AZURE_OPENAI_API_VERSION` (e.g. `2024-10-21`)
   - `AZURE_OPENAI_DEPLOYMENT` (e.g. `gpt-4o`)
4) Redeploy the Space.

The app UI and API will be served from the same Space URL.

### Optional local Docker smoke test

```bash
docker build -t course-prereq-planner .
docker run --rm -p 7860:7860 \
  -e AZURE_OPENAI_ENDPOINT="..." \
  -e AZURE_OPENAI_API_KEY="..." \
  -e AZURE_OPENAI_API_VERSION="2024-10-21" \
  -e AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
  course-prereq-planner
```

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
