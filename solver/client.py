"""OpenAI-compatible Hy3 API client with no benchmark-specific behavior."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from openai import OpenAI


DEFAULT_BASE_URL = "https://tokenhub.tencentmaas.com/v1"


@dataclass(frozen=True)
class Hy3RequestConfig:
    """Configuration for one class of reproducible Hy3 requests."""

    api_key: str = field(repr=False)
    base_url: str = DEFAULT_BASE_URL
    model: str = "hy3"
    temperature: float = 0.9
    top_p: float = 1.0
    max_tokens: int = 32000
    thinking: str = "enabled"
    reasoning_effort: str = "high"
    timeout_seconds: float = 300.0

    @classmethod
    def from_env(
        cls,
        *,
        temperature: float = 0.9,
        top_p: float = 1.0,
        max_tokens: int = 32000,
        thinking: str = "enabled",
        reasoning_effort: str = "high",
        timeout_seconds: float = 300.0,
    ) -> "Hy3RequestConfig":
        api_key = os.environ.get("HY3_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("HY3_API_KEY is not set")
        return cls(
            api_key=api_key,
            base_url=os.environ.get("HY3_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            model=os.environ.get("HY3_MODEL", "hy3"),
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
            timeout_seconds=timeout_seconds,
        )

    def public_dict(self) -> dict[str, Any]:
        """Return request settings safe to persist in experiment outputs."""

        return {
            "base_url": self.base_url,
            "endpoint": "/chat/completions",
            "model": self.model,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
            "thinking": {"type": self.thinking},
            "reasoning_effort": self.reasoning_effort,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True)
class Hy3Response:
    """A complete successful provider response with safe HTTP metadata."""

    status_code: int
    headers: dict[str, str]
    body: dict[str, Any]


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="json", exclude_none=False)
    raise TypeError(f"Unsupported stream chunk type: {type(value).__name__}")


def aggregate_stream_chunks(
    chunks: Iterable[Any],
    *,
    on_chunk: Callable[[int, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Combine provider SSE chunks without discarding the original chunk sequence."""

    raw_chunks: list[dict[str, Any]] = []
    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    response_id: Any = None
    created: Any = None
    model: Any = None
    role = "assistant"
    finish_reason: Any = None
    usage: Any = None

    for chunk in chunks:
        data = _as_dict(chunk)
        raw_chunks.append(data)
        if on_chunk is not None:
            on_chunk(len(raw_chunks), data)
        if data.get("error") is not None:
            raise RuntimeError(f"Provider stream error: {data['error']}")

        response_id = data.get("id") or response_id
        created = data.get("created") or created
        model = data.get("model") or model
        if data.get("usage") is not None:
            usage = data["usage"]

        for choice in data.get("choices") or []:
            if choice.get("finish_reason") is not None:
                finish_reason = choice["finish_reason"]
            delta = choice.get("delta") or {}
            role = delta.get("role") or role
            content = delta.get("content")
            if isinstance(content, str):
                content_parts.append(content)
            reasoning_content = delta.get("reasoning_content")
            if isinstance(reasoning_content, str):
                reasoning_parts.append(reasoning_content)

    if finish_reason is None:
        raise RuntimeError("Provider stream ended without finish_reason")
    if usage is None:
        raise RuntimeError("Provider stream ended without usage")

    return {
        "id": response_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": {
                    "role": role,
                    "content": "".join(content_parts),
                    "reasoning_content": "".join(reasoning_parts) or None,
                },
            }
        ],
        "usage": usage,
        "stream_chunks": raw_chunks,
    }


class Hy3Client:
    """Small, independently reusable wrapper around the Hy3 chat endpoint."""

    def __init__(self, config: Hy3RequestConfig) -> None:
        self.config = config
        self._client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            max_retries=0,
        )

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        on_chunk: Callable[[int, dict[str, Any]], None] | None = None,
    ) -> Hy3Response:
        """Stream one chat completion and retain both aggregate and raw chunks."""

        raw_response = self._client.chat.completions.with_raw_response.create(
            model=self.config.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            max_tokens=self.config.max_tokens,
            stream=True,
            stream_options={"include_usage": True},
            extra_body={
                "thinking": {"type": self.config.thinking},
                "reasoning_effort": self.config.reasoning_effort,
            },
        )
        stream = raw_response.parse()
        try:
            body = aggregate_stream_chunks(stream, on_chunk=on_chunk)
        finally:
            close = getattr(stream, "close", None)
            if callable(close):
                close()
        safe_header_names = (
            "date",
            "request-id",
            "x-request-id",
            "x-tencent-request-id",
        )
        headers = {
            name: value
            for name in safe_header_names
            if (value := raw_response.headers.get(name)) is not None
        }
        return Hy3Response(
            status_code=raw_response.status_code,
            headers=headers,
            body=body,
        )

    def solve(
        self,
        messages: list[dict[str, str]],
        *,
        on_chunk: Callable[[int, dict[str, Any]], None] | None = None,
    ) -> Hy3Response:
        """Backward-compatible solver entry point."""

        return self.complete(messages, on_chunk=on_chunk)
