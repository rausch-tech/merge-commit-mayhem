"""
LLM provider abstraction (Tier 3.9.1).

Dual-provider hinter `LLMClient` Protocol:

- `AnthropicClient` — Cloud (Claude Haiku per default), Anthropic SDK.
- `LocalOpenAIClient` — OpenAI-kompatibler Endpoint (z. B. Ollama mit Gemma 4
  unter `http://localhost:11434/v1`).

Provider-Selektion via Env-Vars (in dieser Reihenfolge):

1. `ANTHROPIC_API_KEY` gesetzt → Anthropic.
2. `LLM_LOCAL_BASE_URL` + `LLM_LOCAL_MODEL` gesetzt → lokal.
3. Sonst → `None`. Caller fällt auf existierende Heuristik / Templates zurück.

Hard timeout 3 s pro Call (`LLM_TIMEOUT_SEC` overridable). Jede Exception
wird zu `None` geschluckt — das Spiel muss ohne LLM laufen, sonst killt
uns die CI ohne API-Key oder ein down-lokaler Inferenz-Server.

Public API:
- `get_default_client() -> LLMClient | None`
- `LLMClient.complete(system, user, max_tokens) -> str | None`
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Final, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SEC: Final[float] = 3.0
DEFAULT_MAX_TOKENS: Final[int] = 256
DEFAULT_ANTHROPIC_MODEL: Final[str] = "claude-haiku-4-5-20251001"


@runtime_checkable
class LLMClient(Protocol):
    """Minimaler Provider-Contract.

    Eine erfolgreiche Completion gibt den text-Body zurück. Jeder Fehler
    (Timeout, Network, API, Auth) wird vom Provider zu `None` geschluckt
    und gelogged — Caller müssen niemals exception-handlen.
    """

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> str | None: ...


class AnthropicClient:
    """Anthropic Messages API client.

    Nutzt urllib statt dem `anthropic` SDK damit wir keine extra Dependency
    in `pyproject.toml` ziehen müssen — wir brauchen nur einen einzigen
    POST. System-Prompt wird als top-level `system`-Feld geschickt, damit
    Anthropic Prompt-Caching (sofern serverseitig aktiv) angreifen kann.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_ANTHROPIC_MODEL,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
        base_url: str = "https://api.anthropic.com/v1/messages",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_sec = timeout_sec
        self._base_url = base_url

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> str | None:
        body = {
            "model": self._model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        req = urllib.request.Request(
            self._base_url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout_sec) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            logger.warning("anthropic completion failed: %s", exc)
            return None

        return _extract_anthropic_text(payload)


class LocalOpenAIClient:
    """OpenAI-kompatibler Client für lokale Inferenz (Ollama, vLLM, …).

    Wir hitten `<base_url>/chat/completions` mit dem Standard-OpenAI-Schema.
    `base_url` MUSS mit dem Versions-Pfad enden (z. B. `…/v1`), damit
    `chat/completions` korrekt drangehängt wird — das matched Ollamas
    eigenes URL-Layout (`http://localhost:11434/v1/chat/completions`).
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout_sec = timeout_sec

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> str | None:
        body = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {"content-type": "application/json"}
        if self._api_key:
            headers["authorization"] = f"Bearer {self._api_key}"
        req = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout_sec) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            logger.warning("local llm completion failed: %s", exc)
            return None

        return _extract_openai_text(payload)


def _extract_anthropic_text(payload: object) -> str | None:
    """Pull the first text block out of an Anthropic Messages response.

    Schema: `{"content": [{"type": "text", "text": "..."}]}`. We accept the
    first `text`-typed block; non-text blocks (tool_use etc.) are ignored.
    """
    if not isinstance(payload, dict):
        return None
    content = payload.get("content")
    if not isinstance(content, list):
        return None
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "text":
            continue
        text = block.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return None


def _extract_openai_text(payload: object) -> str | None:
    """Pull the assistant message out of an OpenAI-format response.

    Schema: `{"choices": [{"message": {"content": "..."}}]}`. Ollama
    matches this. Empty / malformed → None.
    """
    if not isinstance(payload, dict):
        return None
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    return None


def _read_timeout() -> float:
    raw = os.environ.get("LLM_TIMEOUT_SEC")
    if not raw:
        return DEFAULT_TIMEOUT_SEC
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_SEC
    if value <= 0:
        return DEFAULT_TIMEOUT_SEC
    return value


def get_default_client() -> LLMClient | None:
    """Pick a provider from env, or `None` if none configured.

    Order matters: Anthropic wins if both keys are set, because cloud is
    the documented default and avoids surprise local-fallback when an
    operator forgets to unset their dev env. Operators who explicitly
    want the local provider can leave `ANTHROPIC_API_KEY` unset.
    """
    timeout = _read_timeout()

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if anthropic_key:
        model = os.environ.get("ANTHROPIC_MODEL", "").strip() or DEFAULT_ANTHROPIC_MODEL
        return AnthropicClient(api_key=anthropic_key, model=model, timeout_sec=timeout)

    local_url = os.environ.get("LLM_LOCAL_BASE_URL", "").strip()
    local_model = os.environ.get("LLM_LOCAL_MODEL", "").strip()
    if local_url and local_model:
        return LocalOpenAIClient(
            base_url=local_url,
            model=local_model,
            api_key=os.environ.get("LLM_LOCAL_API_KEY", "").strip() or None,
            timeout_sec=timeout,
        )

    return None
