"""uvicorn entry: python -m model_autopsy.backend"""
from __future__ import annotations

import uvicorn

from .config import bootstrap_env

if __name__ == "__main__":
    # Load model_autopsy/.env (MODEL_API_KEY etc.) into the server process.
    # Explicit process env vars still win; nothing secret is printed.
    bootstrap_env()
    uvicorn.run("model_autopsy.backend.api:app", host="127.0.0.1", port=8000,
                reload=False)
