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
