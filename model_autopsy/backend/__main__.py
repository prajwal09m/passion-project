"""uvicorn entry: python -m model_autopsy.backend"""
from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run("model_autopsy.backend.api:app", host="127.0.0.1", port=8000,
                reload=False)
