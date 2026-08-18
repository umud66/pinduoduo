from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class AIGatewayError(RuntimeError):
    pass


@dataclass(slots=True)
class ChatResult:
    text: str
    raw: dict[str, Any]


@dataclass(slots=True)
class ImageResult:
    urls: list[str]
    base64_images: list[str]
    raw: dict[str, Any]


class AIProviderProtocol(Protocol):
    def chat(self, *, model: str, messages: list[dict[str, Any]], temperature: float = 0.2) -> ChatResult: ...

    def generate_image(self, *, model: str, prompt: str, size: str = "1024x1024") -> ImageResult: ...


class OpenAICompatibleProvider:
    def __init__(self, base_url: str, api_key: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def chat(self, *, model: str, messages: list[dict[str, Any]], temperature: float = 0.2) -> ChatResult:
        payload = {"model": model, "messages": messages, "temperature": temperature}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/chat/completions", headers=self.headers, json=payload)
        if response.is_error:
            raise AIGatewayError(f"AI chat request failed: {response.status_code} {response.text[:500]}")
        data = response.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIGatewayError("AI response does not match OpenAI-compatible chat format") from exc
        return ChatResult(text=str(text), raw=data)

    def generate_image(self, *, model: str, prompt: str, size: str = "1024x1024") -> ImageResult:
        payload = {"model": model, "prompt": prompt, "size": size, "n": 1}
        with httpx.Client(timeout=max(self.timeout, 120.0)) as client:
            response = client.post(f"{self.base_url}/images/generations", headers=self.headers, json=payload)
        if response.is_error:
            raise AIGatewayError(f"AI image request failed: {response.status_code} {response.text[:500]}")
        data = response.json()
        urls: list[str] = []
        base64_images: list[str] = []
        for item in data.get("data", []):
            if item.get("url"):
                urls.append(str(item["url"]))
            if item.get("b64_json"):
                base64_images.append(str(item["b64_json"]))
        if not urls and not base64_images:
            raise AIGatewayError("Image provider returned no URL or base64 image")
        return ImageResult(urls=urls, base64_images=base64_images, raw=data)


class AnthropicProvider:
    def __init__(self, base_url: str, api_key: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def chat(self, *, model: str, messages: list[dict[str, Any]], temperature: float = 0.2) -> ChatResult:
        system_parts = [str(m["content"]) for m in messages if m.get("role") == "system"]
        normal_messages = [m for m in messages if m.get("role") != "system"]
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": 2048,
            "temperature": temperature,
            "messages": normal_messages,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/v1/messages", headers=headers, json=payload)
        if response.is_error:
            raise AIGatewayError(f"Anthropic request failed: {response.status_code} {response.text[:500]}")
        data = response.json()
        text = "".join(str(part.get("text", "")) for part in data.get("content", []) if part.get("type") == "text")
        if not text:
            raise AIGatewayError("Anthropic response contains no text")
        return ChatResult(text=text, raw=data)

    def generate_image(self, *, model: str, prompt: str, size: str = "1024x1024") -> ImageResult:
        raise AIGatewayError("Anthropic direct provider does not expose image generation in this adapter")


class GeminiProvider:
    def __init__(self, base_url: str, api_key: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def chat(self, *, model: str, messages: list[dict[str, Any]], temperature: float = 0.2) -> ChatResult:
        parts: list[dict[str, str]] = []
        for message in messages:
            role = str(message.get("role", "user"))
            content = str(message.get("content", ""))
            parts.append({"text": f"[{role}] {content}"})
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": temperature},
        }
        url = f"{self.base_url}/v1beta/models/{model}:generateContent"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, params={"key": self.api_key}, json=payload)
        if response.is_error:
            raise AIGatewayError(f"Gemini request failed: {response.status_code} {response.text[:500]}")
        data = response.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIGatewayError("Gemini response contains no text") from exc
        return ChatResult(text=str(text), raw=data)

    def generate_image(self, *, model: str, prompt: str, size: str = "1024x1024") -> ImageResult:
        raise AIGatewayError("Gemini image generation should be configured through a compatible image endpoint for MVP")


def build_provider(provider_type: str, base_url: str, api_key: str) -> AIProviderProtocol:
    normalized = provider_type.strip().lower()
    if normalized in {"openai", "openai_compatible", "relay"}:
        return OpenAICompatibleProvider(base_url, api_key)
    if normalized == "anthropic":
        return AnthropicProvider(base_url, api_key)
    if normalized == "gemini":
        return GeminiProvider(base_url, api_key)
    raise AIGatewayError(f"Unsupported AI provider type: {provider_type}")
