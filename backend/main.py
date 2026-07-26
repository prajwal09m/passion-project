"""
FastAPI backend for Demand Zone AI Trading Platform.
Loads the trained model at startup and serves prediction endpoints.
Supports both sync POST /api/predict and async task-based POST /api/predict/async.
"""

import sys
import threading
from pathlib import Path

_PARENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PARENT))

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.models import (
    PredictRequest, PredictResponse, HealthResponse,
)
from backend.predict import build_prediction, get_model
from backend.cache import get as cache_get, set as cache_set
from backend.tasks import create_task, update_progress, set_result, set_error, get_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Demand Zone AI Backend...")
    model_state = get_model()
    if model_state:
        _, _, meta = model_state
        logger.info(f"Model loaded: {meta.get('model_name', 'unknown')} "
                     f"({meta.get('features_count', '?')} features)")
    else:
        logger.warning("No serialized model found. Using heuristic fallback.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Demand Zone AI Trading API",
    description="ML-powered demand zone detection and trade prediction",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3007", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health():
    model_state = get_model()
    if model_state:
        _, _, meta = model_state
        return HealthResponse(
            status="ok", model_loaded=True,
            model_name=meta.get("model_name", "unknown"),
            features_count=meta.get("features_count", 0),
        )
    return HealthResponse(status="ok", model_loaded=False, model_name="heuristic fallback", features_count=0)


@app.post("/api/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """Sync prediction endpoint (returns result directly)."""
    symbol = request.symbol.upper().strip()
    if not symbol or len(symbol) > 10:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")

    # Check cache
    cached = cache_get(symbol)
    if cached:
        return cached

    try:
        result = build_prediction(symbol)
        cache_set(symbol, result)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Prediction failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.post("/api/predict/async")
async def predict_async(request: PredictRequest):
    """
    Async prediction endpoint — returns a task ID immediately.
    Poll GET /api/predict/task/{task_id} for progress and result.
    """
    symbol = request.symbol.upper().strip()
    if not symbol or len(symbol) > 10:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")

    # Check cache — if hit, return immediately with result
    cached = cache_get(symbol)
    if cached:
        task_id = create_task(symbol)
        set_result(task_id, cached)
        return {"task_id": task_id, "cached": True}

    # Create task and run in background thread
    task_id = create_task(symbol)

    def _run():
        try:
            result = build_prediction(
                symbol,
                on_progress=lambda stage, pct: update_progress(task_id, stage, pct),
            )
            cache_set(symbol, result)
            set_result(task_id, result)
        except Exception as e:
            logger.exception(f"Async prediction failed for {symbol}: {e}")
            set_error(task_id, str(e))

    threading.Thread(target=_run, daemon=True).start()
    return {"task_id": task_id, "cached": False}


@app.get("/api/predict/task/{task_id}")
async def get_task(task_id: str):
    """Poll for task progress and result."""
    status = get_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Task not found")

    response = {
        "task_id": task_id,
        "symbol": status["symbol"],
        "stage": status["stage"],
        "progress": status["progress"],
        "done": status["done"],
    }

    if status["done"]:
        if status["error"]:
            response["error"] = status["error"]
        else:
            response["result"] = status["result"].model_dump() if status["result"] else None

    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail, "detail": None})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
