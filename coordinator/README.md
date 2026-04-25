# Coordinator

FastAPI orchestrator for Lethe. Hosts the consensus coordinator and (eventually) AXL node #0.

## Setup

```bash
cd coordinator
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload --port 8000
```

Then hit:

- `http://localhost:8000/` — hello world
- `http://localhost:8000/health` — health check
- `http://localhost:8000/docs` — interactive API docs
