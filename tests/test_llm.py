"""
Tests for app/game/llm.py — provider abstraction.

We never hit the network. Each test patches `urllib.request.urlopen`
to return a canned response, or asserts that env-driven selection picks
the correct concrete client without any HTTP at all.
"""

from __future__ import annotations

import io
import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any
from urllib.error import URLError

import pytest

from app.game import llm


@contextmanager
def _fake_urlopen(
    monkeypatch: pytest.MonkeyPatch,
    *,
    response: dict[str, Any] | None = None,
    raises: BaseException | None = None,
) -> Iterator[list[dict[str, Any]]]:
    """Patch urllib.request.urlopen with a canned response or exception.

    Yields a list of intercepted call records (one dict per call) so a
    test can assert on URL / headers / body without subclassing anything.
    """
    calls: list[dict[str, Any]] = []

    class _FakeResp:
        def __init__(self, data: bytes) -> None:
            self._buf = io.BytesIO(data)

        def read(self) -> bytes:
            return self._buf.read()

        def __enter__(self) -> _FakeResp:
            return self

        def __exit__(self, *_: object) -> None:
            return None

    def _opener(req: Any, timeout: float = 0.0) -> _FakeResp:
        body = req.data.decode("utf-8") if req.data else ""
        calls.append(
            {
                "url": req.full_url,
                "headers": dict(req.headers),
                "body": json.loads(body) if body else None,
                "timeout": timeout,
            }
        )
        if raises is not None:
            raise raises
        assert response is not None, "either response or raises must be set"
        return _FakeResp(json.dumps(response).encode("utf-8"))

    monkeypatch.setattr(llm.urllib.request, "urlopen", _opener)
    yield calls


# --- AnthropicClient --------------------------------------------------------


def test_anthropic_client_returns_text_block(monkeypatch: pytest.MonkeyPatch) -> None:
    response = {
        "id": "msg_x",
        "content": [{"type": "text", "text": "hallo welt"}],
    }
    with _fake_urlopen(monkeypatch, response=response) as calls:
        client = llm.AnthropicClient(api_key="sk-test", model="claude-haiku-4-5-20251001")
        out = client.complete(system="be terse", user="say hi", max_tokens=32)

    assert out == "hallo welt"
    assert len(calls) == 1
    call = calls[0]
    assert call["url"] == "https://api.anthropic.com/v1/messages"
    # x-api-key + anthropic-version are mandatory wire-fields.
    assert call["headers"]["X-api-key"] == "sk-test"
    assert call["headers"]["Anthropic-version"] == "2023-06-01"
    assert call["body"]["model"] == "claude-haiku-4-5-20251001"
    assert call["body"]["max_tokens"] == 32
    assert call["body"]["system"] == "be terse"
    assert call["body"]["messages"] == [{"role": "user", "content": "say hi"}]
    assert call["timeout"] == llm.DEFAULT_TIMEOUT_SEC


def test_anthropic_client_skips_non_text_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    response = {
        "content": [
            {"type": "tool_use", "id": "x", "name": "noop", "input": {}},
            {"type": "text", "text": "nach dem tool"},
        ]
    }
    with _fake_urlopen(monkeypatch, response=response):
        out = llm.AnthropicClient(api_key="k").complete(system="s", user="u")
    assert out == "nach dem tool"


def test_anthropic_client_swallows_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    with _fake_urlopen(monkeypatch, raises=URLError("connection refused")):
        out = llm.AnthropicClient(api_key="k").complete(system="s", user="u")
    assert out is None


def test_anthropic_client_swallows_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    with _fake_urlopen(monkeypatch, raises=TimeoutError("slow")):
        out = llm.AnthropicClient(api_key="k").complete(system="s", user="u")
    assert out is None


def test_anthropic_client_handles_empty_content(monkeypatch: pytest.MonkeyPatch) -> None:
    with _fake_urlopen(monkeypatch, response={"content": []}):
        out = llm.AnthropicClient(api_key="k").complete(system="s", user="u")
    assert out is None


def test_anthropic_client_handles_blank_text(monkeypatch: pytest.MonkeyPatch) -> None:
    response = {"content": [{"type": "text", "text": "   "}]}
    with _fake_urlopen(monkeypatch, response=response):
        out = llm.AnthropicClient(api_key="k").complete(system="s", user="u")
    assert out is None


# --- LocalOpenAIClient ------------------------------------------------------


def test_local_client_appends_chat_completions(monkeypatch: pytest.MonkeyPatch) -> None:
    response = {"choices": [{"message": {"role": "assistant", "content": "ja klar"}}]}
    with _fake_urlopen(monkeypatch, response=response) as calls:
        client = llm.LocalOpenAIClient(base_url="http://localhost:11434/v1/", model="gemma3:4b")
        out = client.complete(system="be brief", user="hi")

    assert out == "ja klar"
    assert len(calls) == 1
    call = calls[0]
    assert call["url"] == "http://localhost:11434/v1/chat/completions"
    assert "Authorization" not in call["headers"]
    assert call["body"]["model"] == "gemma3:4b"
    assert call["body"]["messages"][0] == {"role": "system", "content": "be brief"}
    assert call["body"]["messages"][1] == {"role": "user", "content": "hi"}


def test_local_client_sends_bearer_when_api_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    response = {"choices": [{"message": {"content": "ok"}}]}
    with _fake_urlopen(monkeypatch, response=response) as calls:
        client = llm.LocalOpenAIClient(base_url="http://example/v1", model="m", api_key="secret")
        client.complete(system="s", user="u")

    assert calls[0]["headers"]["Authorization"] == "Bearer secret"


def test_local_client_swallows_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    with _fake_urlopen(monkeypatch, raises=URLError("nope")):
        out = llm.LocalOpenAIClient(base_url="http://x/v1", model="m").complete(
            system="s", user="u"
        )
    assert out is None


def test_local_client_handles_empty_choices(monkeypatch: pytest.MonkeyPatch) -> None:
    with _fake_urlopen(monkeypatch, response={"choices": []}):
        out = llm.LocalOpenAIClient(base_url="http://x/v1", model="m").complete(
            system="s", user="u"
        )
    assert out is None


def test_local_client_handles_malformed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    with _fake_urlopen(monkeypatch, response={"unexpected": True}):
        out = llm.LocalOpenAIClient(base_url="http://x/v1", model="m").complete(
            system="s", user="u"
        )
    assert out is None


# --- get_default_client (env-driven selection) ------------------------------


def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "LLM_LOCAL_BASE_URL",
        "LLM_LOCAL_MODEL",
        "LLM_LOCAL_API_KEY",
        "LLM_TIMEOUT_SEC",
    ):
        monkeypatch.delenv(key, raising=False)


def test_default_client_returns_none_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    assert llm.get_default_client() is None


def test_default_client_picks_anthropic_when_key_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-xyz")
    client = llm.get_default_client()
    assert isinstance(client, llm.AnthropicClient)


def test_default_client_anthropic_uses_custom_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-xyz")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    client = llm.get_default_client()
    assert isinstance(client, llm.AnthropicClient)
    assert client._model == "claude-sonnet-4-6"  # type: ignore[attr-defined]


def test_default_client_picks_local_when_only_local_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_LOCAL_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_LOCAL_MODEL", "gemma3:4b")
    client = llm.get_default_client()
    assert isinstance(client, llm.LocalOpenAIClient)


def test_default_client_anthropic_wins_over_local(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk")
    monkeypatch.setenv("LLM_LOCAL_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_LOCAL_MODEL", "gemma3:4b")
    client = llm.get_default_client()
    assert isinstance(client, llm.AnthropicClient)


def test_default_client_partial_local_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_LOCAL_BASE_URL", "http://localhost:11434/v1")
    # missing LLM_LOCAL_MODEL — must not pick local
    assert llm.get_default_client() is None


def test_default_client_respects_timeout_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("LLM_TIMEOUT_SEC", "1.5")
    client = llm.get_default_client()
    assert isinstance(client, llm.AnthropicClient)
    assert client._timeout_sec == pytest.approx(1.5)  # type: ignore[attr-defined]


def test_default_client_invalid_timeout_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("LLM_TIMEOUT_SEC", "nope")
    client = llm.get_default_client()
    assert isinstance(client, llm.AnthropicClient)
    assert client._timeout_sec == pytest.approx(llm.DEFAULT_TIMEOUT_SEC)  # type: ignore[attr-defined]


# --- Protocol conformance ---------------------------------------------------


@pytest.mark.parametrize(
    "factory",
    [
        lambda: llm.AnthropicClient(api_key="k"),
        lambda: llm.LocalOpenAIClient(base_url="http://x/v1", model="m"),
    ],
)
def test_clients_satisfy_protocol(factory: Callable[[], object]) -> None:
    assert isinstance(factory(), llm.LLMClient)
