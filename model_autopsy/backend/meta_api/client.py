"""Meta Model API adapter (Muse Spark) — Responses API + tool calling.

Endpoint facts verified against Meta's official developer docs
(dev.meta.ai): base https://api.meta.ai/v1, Responses API at
POST /responses, bearer-token auth, flat `function` tool definitions, the
model's tool call arrives as a `function_call` output item whose
`arguments` is a JSON-encoded string, and results are returned as
`function_call_output` items matched by `call_id`.

The adapter never fabricates a Meta response: without MODEL_API_KEY every
call raises MetaUnavailable and callers must surface that honestly.
"""
from __future__ import annotations

import json
import time

import httpx

from .. import config

RESPONSES_ENDPOINT = "/responses"
MODELS_ENDPOINT = "/models"
REQUEST_TIMEOUT = 90.0
MAX_RETRIES = 3                       # bounded retries for transient failures
RETRY_BACKOFF_SECONDS = 1.0
_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class MetaUnavailable(RuntimeError):
    """No API key configured (or network/API error) — surfaced to the UI.

    `status_code` is set when a provider HTTP status was the cause (None for
    missing-key or network failures), so callers can SAFELY distinguish
    continuation-state problems (e.g. an expired/invalid previous_response_id)
    from outages — never by inferring from the message text alone."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _headers() -> dict[str, str]:
    key = config.meta_api_key()
    if not key:
        raise MetaUnavailable(
            "MODEL_API_KEY is not configured. Set it in the backend "
            "environment (see model_autopsy/.env.example) and restart, then "
            "use the connection test on the Integrations page.")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _url() -> str:
    return config.meta_base_url() + RESPONSES_ENDPOINT


def test_connection() -> dict:
    """Cheap live check: GET /models with the configured key (no spend)."""
    try:
        headers = _headers()
    except MetaUnavailable as exc:
        return {"ok": False, "connected": False, "detail":
                str(exc)[:300]}
    try:
        resp = httpx.get(config.meta_base_url() + MODELS_ENDPOINT,
                         headers=headers, timeout=30.0)
    except httpx.HTTPError as exc:
        return {"ok": False, "connected": False, "error": type(exc).__name__,
                "detail": str(exc)[:200]}
    if resp.status_code != 200:
        return {"ok": False, "connected": False,
                "status_code": resp.status_code,
                "detail": resp.text[:200]}
    try:
        models = resp.json()
    except json.JSONDecodeError:
        models = {"raw": resp.text[:200]}
    ids = []
    data = models.get("data") if isinstance(models, dict) else None
    if isinstance(data, list):
        ids = [m.get("id") for m in data if isinstance(m, dict)]
    return {"ok": True, "connected": True, "base_url": config.meta_base_url(),
            "model_id": config.meta_model_id(), "available_model_ids": ids,
            "tested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def create_response(*, model: str, input_items, tools: list[dict],
                    previous_response_id: str | None = None,
                    instructions: str | None = None, temperature: float = 0.2,
                    max_output_tokens: int = 2000) -> dict:
    """One Responses API call with bounded transient-retry handling.

    408/429/5xx get up to MAX_RETRIES attempts with linear backoff; other
    statuses fail fast. All failures surface as MetaUnavailable with a
    sanitized, actionable detail (status + short body, never the key)."""
    body: dict = {"model": model, "input": input_items, "tools": tools,
                  "tool_choice": "auto", "temperature": temperature,
                  "max_output_tokens": max_output_tokens}
    if previous_response_id:
        body["previous_response_id"] = previous_response_id
    if instructions:
        body["instructions"] = instructions
    headers = _headers()          # raises MetaUnavailable without a key
    last_error = "unknown error"
    latency_total = 0.0           # wall time across ALL attempts of this request
    attempts_used = 0
    for attempt in range(1, MAX_RETRIES + 1):
        t0 = time.perf_counter()
        try:
            resp = httpx.post(_url(), headers=headers, json=body,
                              timeout=REQUEST_TIMEOUT)
        except httpx.HTTPError as exc:
            raise MetaUnavailable(f"{type(exc).__name__}: {exc}") from exc
        latency_total += time.perf_counter() - t0
        attempts_used = attempt
        if resp.status_code == 200:
            try:
                payload = resp.json()
            except json.JSONDecodeError as exc:
                raise MetaUnavailable(
                    f"non-JSON response from Meta: {exc}") from exc
            payload.setdefault("_request_perf", {
                "latency_s": round(latency_total, 3),
                "attempts": attempts_used})
            return payload
        last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
        if resp.status_code not in _RETRYABLE_STATUS:
            break
        if attempt < MAX_RETRIES:
            retry_after = resp.headers.get("retry-after")
            delay = (float(retry_after) if retry_after and
                     retry_after.replace(".", "").isdigit()
                     else RETRY_BACKOFF_SECONDS * attempt)
            time.sleep(min(delay, 10.0))
    message = last_error
    if attempts_used > 1:
        message += f" (after {attempts_used} attempts)"
    raise MetaUnavailable(message, status_code=resp.status_code)


# Chain-continuation state failures: non-transient, non-auth request errors
# observed while a `previous_response_id` was in play. These are the only
# failures for which a context-delta turn should attempt its full-context
# fallback (docs: non-retryable statuses must not be retried identically).
CHAIN_STATE_ERROR_STATUSES = {400, 404, 409, 410, 413}


def extract_function_calls(response: dict) -> list[dict]:
    """Pull tool calls out of a Responses payload (validated minimally)."""
    calls: list[dict] = []
    for item in response.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "function_call":
            continue
        raw_args = item.get("arguments") or "{}"
        try:
            arguments = json.loads(raw_args)
        except json.JSONDecodeError:
            arguments = {"_invalid_json": str(raw_args)[:200]}
        calls.append({"call_id": str(item.get("call_id") or ""),
                      "name": str(item.get("name") or ""),
                      "arguments": arguments})
    return calls


def extract_message_text(response: dict) -> str:
    """Extract the assistant message text (recorded verbatim, no edits)."""
    chunks: list[str] = []
    for item in response.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if isinstance(part, dict) and part.get("type") == "output_text":
                chunks.append(str(part.get("text") or ""))
    return "\n".join(chunks)


def response_id(response: dict) -> str | None:
    return response.get("id")


def usage(response: dict) -> dict:
    """Provider-reported token usage, flattened from nested detail dicts.

    Known Responses-style wrappers (`usage.input_tokens_details.cached_tokens`)
    become dotted keys like `input_tokens_details.cached_tokens` so cached-token
    accounting is captured honestly when the provider reports it and absent
    when it does not. Nothing is invented: numbers only, no placeholders."""
    u = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    out: dict = {}
    for key, value in u.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            out[key] = value
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if (isinstance(sub_value, (int, float))
                        and not isinstance(sub_value, bool)):
                    out[f"{key}.{sub_key}"] = sub_value
    return out
