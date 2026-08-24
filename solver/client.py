"""OpenAI-compatible Hy3 API client with no benchmark-specific behavior."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

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
    max_tokens: int = 4096
    thinking: str = "enabled"
    reasoning_effort: str = "high"
    timeout_seconds: float = 300.0

    @classmethod
    def from_env(
        cls,
        *,
        temperature: float = 0.9,
        top_p: float = 1.0,
        max_tokens: int = 4096,
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
            "stream": False,
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

    def solve(self, messages: list[dict[str, str]]) -> Hy3Response:
        """Submit one mathematics problem and retain the full parsed API response."""

        raw_response = self._client.chat.completions.with_raw_response.create(
            model=self.config.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            max_tokens=self.config.max_tokens,
            stream=False,
            extra_body={
                "thinking": {"type": self.config.thinking},
                "reasoning_effort": self.config.reasoning_effort,
            },
        )
        response = raw_response.parse()
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
            body=response.model_dump(mode="json", exclude_none=False),
        )
