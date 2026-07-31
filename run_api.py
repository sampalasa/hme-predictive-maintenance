"""FastAPI service entry point: `python run_api.py`.

Serves the public REST API on http://127.0.0.1:8000 (Swagger UI at /docs).
Run alongside the Flask web app (`python run.py`, port 5000) — they share
the same SQLite database and ML artifacts.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.api_fastapi.main:app", host="127.0.0.1", port=8000, reload=False)
