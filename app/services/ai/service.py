from __future__ import annotations

from sqlalchemy import select

from app.core.secrets import SecretStore
from app.db.database import session_scope
from app.db.models import AIProvider
from app.services.ai.gateway import AIProviderProtocol, build_provider


class AIProviderService:
    def __init__(self, secret_store: SecretStore | None = None) -> None:
        self.secret_store = secret_store or SecretStore()

    def create_provider(
        self,
        *,
        name: str,
        provider_type: str,
        base_url: str,
        api_key: str,
        chat_model: str | None,
        vision_model: str | None,
        image_model: str | None,
    ) -> AIProvider:
        with session_scope() as session:
            provider = AIProvider(
                name=name,
                provider_type=provider_type,
                base_url=base_url.rstrip("/"),
                api_key_encrypted=self.secret_store.encrypt(api_key),
                chat_model=chat_model,
                vision_model=vision_model,
                image_model=image_model,
            )
            session.add(provider)
            session.flush()
            session.expunge(provider)
            return provider

    def update_provider(
        self,
        provider_id: int,
        *,
        name: str | None = None,
        provider_type: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        chat_model: str | None = None,
        vision_model: str | None = None,
        image_model: str | None = None,
        enabled: bool | None = None,
    ) -> AIProvider:
        with session_scope() as session:
            provider = session.get(AIProvider, provider_id)
            if provider is None:
                raise LookupError("AI provider not found")
            if name is not None:
                provider.name = name
            if provider_type is not None:
                provider.provider_type = provider_type
            if base_url is not None:
                provider.base_url = base_url.rstrip("/")
            if api_key is not None and api_key.strip():
                provider.api_key_encrypted = self.secret_store.encrypt(api_key.strip())
            if chat_model is not None:
                provider.chat_model = chat_model or None
            if vision_model is not None:
                provider.vision_model = vision_model or None
            if image_model is not None:
                provider.image_model = image_model or None
            if enabled is not None:
                provider.enabled = enabled
            session.flush()
            session.expunge(provider)
            return provider

    def delete_provider(self, provider_id: int) -> None:
        with session_scope() as session:
            provider = session.get(AIProvider, provider_id)
            if provider is None:
                raise LookupError("AI provider not found")
            session.delete(provider)

    def list_providers(self) -> list[AIProvider]:
        with session_scope() as session:
            providers = session.scalars(select(AIProvider).order_by(AIProvider.id)).all()
            for provider in providers:
                session.expunge(provider)
            return list(providers)

    def get_runtime_provider(self, provider_id: int) -> tuple[AIProvider, AIProviderProtocol]:
        with session_scope() as session:
            provider = session.get(AIProvider, provider_id)
            if provider is None:
                raise LookupError("AI provider not found")
            api_key = self.secret_store.decrypt(provider.api_key_encrypted)
            runtime = build_provider(provider.provider_type, provider.base_url, api_key)
            session.expunge(provider)
            return provider, runtime
