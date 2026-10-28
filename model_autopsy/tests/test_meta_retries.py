"""Meta adapter retry/backoff tests (Phase 5, offline).

Retries are bounded and only for transient statuses: 429 then success; five
hundreds exhaust retries; non-retryable statuses fail fast. No network and
no live key is ever needed — the request path is stubbed at the httpx layer.
"""
from __future__ import annotations

import pytest

from model_autopsy.backend import config
from model_autopsy.backend.meta_api import client as meta_client


class _Resp:
    def __init__(self, status_code=200, json_data=None, text="", hdrs=None):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text
        self.headers = hdrs or {}

    def json(self):
        return self._json


@pytest.fixture()
def with_key(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    monkeypatch.setattr(meta_client.time, "sleep", lambda s: None)
    return None


def test_retry_on_429_then_success(with_key, monkeypatch):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(url)
        if len(calls) < 3:
            return _Resp(429, text="rate limited", hdrs={"retry-after": "0.05"})
        return _Resp(200, {"id": "resp_ok", "output": []})

    monkeypatch.setattr(meta_client.httpx, "post", fake_post)
    out = meta_client.create_response(model="x", input_items=[],
                                      tools=[])
    assert out["id"] == "resp_ok" and len(calls) == 3


def test_exhausted_retries_raise(with_key, monkeypatch):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(url)
        return _Resp(503, text="overloaded")

    monkeypatch.setattr(meta_client.httpx, "post", fake_post)
    with pytest.raises(meta_client.MetaUnavailable, match="503"):
        meta_client.create_response(model="x", input_items=[], tools=[])
    assert len(calls) == meta_client.MAX_RETRIES   # bounded, not unbounded


def test_non_retryable_fails_fast(with_key, monkeypatch):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(url)
        return _Resp(401, text="unauthorized")

    monkeypatch.setattr(meta_client.httpx, "post", fake_post)
    with pytest.raises(meta_client.MetaUnavailable, match="401"):
        meta_client.create_response(model="x", input_items=[], tools=[])
    assert len(calls) == 1


def test_error_never_contains_the_key(with_key, monkeypatch):
    def fake_post(url, headers=None, json=None, timeout=None):
        raise meta_client.httpx.HTTPError("connection refused")

    monkeypatch.setattr(meta_client.httpx, "post",
                        lambda *a, **k: (_ for _ in ()).throw(
                            meta_client.httpx.ConnectError("refused")))
    with pytest.raises(meta_client.MetaUnavailable) as e:
        meta_client.create_response(model="x", input_items=[], tools=[])
    assert "0" * 40 not in str(e.value)


def test_schemas_generate_from_single_source():
    ml = {s["name"]: s for s in meta_tool_schemas_safe()}
    sw = {s["name"]: s for s in meta_tool_schemas_safe("software")}
    assert "propose_hypothesis" in ml and "propose_hypothesis" in sw
    assert "deploy" not in {n for n in ml} | {n for n in sw}


def meta_tool_schemas_safe(mode="ml"):
    from model_autopsy.backend import tools_registry
    return tools_registry.meta_tool_schemas(mode)
