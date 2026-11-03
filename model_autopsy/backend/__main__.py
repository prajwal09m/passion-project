"""uvicorn entry: python -m model_autopsy.backend"""
from __future__ import annotations

import uvicorn

from .config import bootstrap_env

if __name__ == "__main__":
    # Load model_autopsy/.env (MODEL_API_KEY etc.) into the server process.
    # Explicit process env vars still win; nothing secret is printed.
    import os as _os
    bootstrap_env()
    # Render/HF free hosting sets $PORT and requires 0.0.0.0; local default
    # stays loopback 127.0.0.1:8000.
    _raw = (_os.environ.get("PORT", "") or "").strip()
    try:
        _port = int(_raw or "8000")
        if _port <= 0 or _port > 65535:
            raise ValueError
    except ValueError:
        _raw, _port = "", 8000
    # Only bind 0.0.0.0 when hosting asks for it; local runs stay loopback.
    # EC2/AWS: set MODEL_AUTOPSY_HOST=0.0.0.0 (and PORT=8000 or 80).
    # Render/HF: set PORT (non-8000) and host follows automatically.
    _explicit_host = (_os.environ.get("MODEL_AUTOPSY_HOST", "") or "").strip()
    if _explicit_host:
        _host = _explicit_host
    else:
        _host = "0.0.0.0" if (_raw and _port != 8000) else "127.0.0.1"
    if not _raw:
        _port = 8000
    uvicorn.run("model_autopsy.backend.api:app", host=_host, port=_port,
                reload=False)
