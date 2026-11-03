"""Provider-independent inference interfaces (Phase 9).

The investigation engine depends on this interface, never on one
provider's response shape. Adapters translate provider specifics
(request format, response parsing, tool calling, continuation, usage,
errors/retries, structured outputs). Credentials are NEVER handled here:
callers supply keys/ transports; nothing is printed, stored, or logged.
"""
from __future__ import annotations


class ProviderError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None,
                 retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class InferenceProvider:
    """Interface every provider adapter implements."""
    name = "unknown"

    def __init__(self, config: dict | None = None):
        self.config = dict(config or {})

    def capabilities(self) -> dict:
        """E.g. tool_calling, structured_outputs, continuation, usage_parts."""
        raise NotImplementedError

    def create_response(self, **kwargs) -> dict:
        """Normalized response: {id, status, output_text, tool_calls,
        usage{input_tokens, output_tokens, cached_tokens}, raw?}."""
        raise NotImplementedError

    @staticmethod
    def normalize(raw: dict) -> dict:
        """Adapter-specific raw -> normalized mapping helper contract."""
        raise NotImplementedError

    def supports(self, capability: str) -> bool:
        return bool(self.capabilities().get(capability, False))


class MetaProvider(InferenceProvider):
    """Meta Model API adapter over the existing backend transport."""
    name = "meta"

    def capabilities(self) -> dict:
        return {"tool_calling": True, "structured_outputs": True,
                "continuation": True, "cached_usage": True,
                "incomplete_detection": True}

    def create_response(self, **kwargs) -> dict:
        from ..meta_api import client as meta_client
        try:
            return meta_client.create_response(**kwargs)
        except Exception as exc:
            raise ProviderError(str(exc),
                                status_code=getattr(exc, "status_code", None),
                                retryable=getattr(exc, "status_code", None) in (429, 500, 502, 503)) from exc

    @staticmethod
    def normalize(raw: dict) -> dict:
        usage = raw.get("usage") or {}
        details = usage.get("input_tokens_details") or {}
        return {"id": raw.get("id"), "status": raw.get("status"),
                "output_text": ((raw.get("output") or [{}])[0].get("content") or [{}])[0].get("text", "")
                if isinstance(raw.get("output"), list) else raw.get("message_text", ""),
                "usage": {"input_tokens": usage.get("input_tokens", 0),
                          "output_tokens": usage.get("output_tokens", 0),
                          "cached_tokens": details.get("cached_tokens", 0)},
                "incomplete": str(raw.get("status") or "").lower() == "incomplete"}


class GroqProvider(InferenceProvider):
    """Groq OpenAI-compatible chat completions adapter.

    Uses only the official endpoint; the transport is injectable so tests
    never touch the network. Requires a caller-supplied key at call time.
    """
    name = "groq"
    CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

    def capabilities(self) -> dict:
        return {"tool_calling": True, "structured_outputs": False,
                "continuation": False, "cached_usage": False,
                "incomplete_detection": True}

    def create_response(self, model: str, messages: list, api_key: str | None = None,
                        request_fn=None, **kwargs) -> dict:
        import json
        import urllib.request
        key = api_key or self.config.get("api_key")
        if not key and request_fn is None:
            raise ProviderError("no API key supplied to GroqProvider")
        body = {"model": model, "messages": messages,
                "temperature": kwargs.get("temperature", 0.2),
                "max_tokens": kwargs.get("max_tokens", 2000)}
        if request_fn is not None:
            raw = request_fn(self.CHAT_URL, body)
        else:
            req = urllib.request.Request(
                self.CHAT_URL, data=json.dumps(body).encode(),
                headers={"Authorization": "Bearer " + key,
                         "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    raw = json.loads(resp.read().decode())
            except Exception as exc:
                raise ProviderError(f"groq request failed: {type(exc).__name__}",
                                    retryable=True) from exc
        return self.normalize(raw)

    @staticmethod
    def normalize(raw: dict) -> dict:
        choice = ((raw.get("choices") or [{}])[0] or {})
        usage = raw.get("usage") or {}
        return {"id": raw.get("id"), "status": None,
                "finish_reason": choice.get("finish_reason"),
                "output_text": (choice.get("message") or {}).get("content") or "",
                "tool_calls": (choice.get("message") or {}).get("tool_calls") or [],
                "usage": {"input_tokens": usage.get("prompt_tokens", 0),
                          "output_tokens": usage.get("completion_tokens", 0),
                          "cached_tokens": 0},
                "incomplete": choice.get("finish_reason") == "length"}


class OllamaProvider(InferenceProvider):
    """Local Ollama adapter (optional investigator). No cloud calls."""
    name = "ollama"

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.host = (config or {}).get("host", "http://localhost:11434")

    def capabilities(self) -> dict:
        return {"tool_calling": False, "structured_outputs": False,
                "continuation": False, "cached_usage": False,
                "incomplete_detection": False}

    def create_response(self, model: str, messages: list, request_fn=None,
                        **kwargs) -> dict:
        import json
        import urllib.request
        body = {"model": model, "messages": messages, "stream": False}
        if request_fn is not None:
            raw = request_fn(self.host + "/api/chat", body)
        else:
            req = urllib.request.Request(
                self.host + "/api/chat", data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    raw = json.loads(resp.read().decode())
            except Exception as exc:
                raise ProviderError(
                    f"ollama request failed (is ollama running at {self.host}?): "
                    f"{type(exc).__name__}") from exc
        return self.normalize(raw)

    @staticmethod
    def normalize(raw: dict) -> dict:
        return {"id": None, "status": "completed",
                "output_text": (raw.get("message") or {}).get("content") or "",
                "tool_calls": [],
                "usage": {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0},
                "incomplete": False,
                "note": "local model: no provider usage accounting"}


_PROVIDERS = {"meta": MetaProvider, "groq": GroqProvider, "ollama": OllamaProvider}


def get_provider(name: str, config: dict | None = None) -> InferenceProvider:
    try:
        return _PROVIDERS[name](config)
    except KeyError:
        raise LookupError(f"unknown provider {name!r}; supported: "
                          f"{sorted(_PROVIDERS)}") from None
