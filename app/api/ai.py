from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.ai.gateway import AIGatewayError
from app.services.ai.service import AIProviderService

router = APIRouter(tags=["ai"])
service = AIProviderService()


class ProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    provider_type: str = "openai_compatible"
    base_url: str = Field(min_length=4)
    api_key: str = Field(min_length=1)
    chat_model: str | None = None
    vision_model: str | None = None
    image_model: str | None = None


class ProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    provider_type: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    chat_model: str | None = None
    vision_model: str | None = None
    image_model: str | None = None
    enabled: bool | None = None


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str | None = None


class ImageRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str | None = None
    size: str = "1024x1024"


def _provider_payload(p) -> dict[str, object]:
    return {
        "id": p.id,
        "name": p.name,
        "provider_type": p.provider_type,
        "base_url": p.base_url,
        "chat_model": p.chat_model,
        "vision_model": p.vision_model,
        "image_model": p.image_model,
        "enabled": p.enabled,
        "has_api_key": bool(p.api_key_encrypted),
    }


@router.get("/ai/providers")
def list_providers() -> list[dict[str, object]]:
    return [_provider_payload(p) for p in service.list_providers()]


@router.post("/ai/providers")
def create_provider(payload: ProviderCreate) -> dict[str, object]:
    provider = service.create_provider(**payload.model_dump())
    return _provider_payload(provider)


@router.put("/ai/providers/{provider_id}")
def update_provider(provider_id: int, payload: ProviderUpdate) -> dict[str, object]:
    try:
        provider = service.update_provider(provider_id, **payload.model_dump())
        return _provider_payload(provider)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/ai/providers/{provider_id}")
def delete_provider(provider_id: int) -> dict[str, object]:
    try:
        service.delete_provider(provider_id)
        return {"ok": True}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/ai/providers/{provider_id}/test")
def test_provider(provider_id: int) -> dict[str, object]:
    try:
        provider, runtime = service.get_runtime_provider(provider_id)
        if not provider.chat_model:
            raise AIGatewayError("请先配置 chat_model")
        result = runtime.chat(
            model=provider.chat_model,
            messages=[{"role": "user", "content": "只回复 OK"}],
            temperature=0,
        )
        return {"ok": True, "response": result.text[:200]}
    except (LookupError, AIGatewayError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ai/providers/{provider_id}/chat")
def chat(provider_id: int, payload: ChatRequest) -> dict[str, object]:
    try:
        provider, runtime = service.get_runtime_provider(provider_id)
        model = payload.model or provider.chat_model
        if not model:
            raise AIGatewayError("未配置聊天模型")
        result = runtime.chat(model=model, messages=[{"role": "user", "content": payload.prompt}])
        return {"text": result.text}
    except (LookupError, AIGatewayError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ai/providers/{provider_id}/images")
def generate_image(provider_id: int, payload: ImageRequest) -> dict[str, object]:
    try:
        provider, runtime = service.get_runtime_provider(provider_id)
        model = payload.model or provider.image_model
        if not model:
            raise AIGatewayError("未配置图片模型")
        result = runtime.generate_image(model=model, prompt=payload.prompt, size=payload.size)
        return {"urls": result.urls, "base64_images": result.base64_images}
    except (LookupError, AIGatewayError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
