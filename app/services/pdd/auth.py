from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.secrets import SecretStore
from app.db.models import Shop
from app.db.pdd_auth_models import PddApplication, PddAuthorizationSession, PddShopAuthorization
from app.services.pdd.client import PddClient, PddCredentials
from app.services.pdd.auth_protocol import DEFAULT_SHOP_AUTH_URL, build_shop_authorization_url, parse_token_payload, utcnow_naive

STATE_TTL_MINUTES = 30

class PddAuthorizationService:
    def __init__(self, *, secret_store: SecretStore | None = None, client_factory=PddClient) -> None:
        self.secret_store = secret_store or SecretStore()
        self.client_factory = client_factory

    def get_application(self, session: Session) -> PddApplication | None:
        return session.scalar(select(PddApplication).order_by(PddApplication.id).limit(1))

    def save_application(self, session: Session, *, client_id: str, client_secret: str | None, redirect_uri: str, auth_web_url: str | None = None) -> PddApplication:
        client_id = client_id.strip()
        redirect_uri = redirect_uri.strip()
        if not client_id or not redirect_uri:
            raise ValueError("Client ID 和回调地址不能为空")
        app = self.get_application(session)
        if app is None:
            if not client_secret:
                raise ValueError("首次配置必须填写 Client Secret")
            app = PddApplication(
                client_id=client_id,
                client_secret_encrypted=self.secret_store.encrypt(client_secret.strip()),
                redirect_uri=redirect_uri,
                auth_web_url=(auth_web_url or DEFAULT_SHOP_AUTH_URL).strip(),
            )
            session.add(app)
        else:
            identity_changed = app.client_id != client_id
            secret_changed = bool(client_secret and client_secret.strip())
            app.client_id = client_id
            app.redirect_uri = redirect_uri
            if secret_changed:
                app.client_secret_encrypted = self.secret_store.encrypt(client_secret.strip())
            if auth_web_url and auth_web_url.strip():
                app.auth_web_url = auth_web_url.strip()

            authorizations = session.scalars(
                select(PddShopAuthorization).where(PddShopAuthorization.application_id == app.id)
            ).all()
            for auth in authorizations:
                shop = session.get(Shop, auth.shop_id)
                if identity_changed:
                    auth.status = "reauthorization_required"
                    auth.access_token_encrypted = None
                    auth.refresh_token_encrypted = None
                    auth.last_error = "开放平台 Client ID 已变更，请重新授权店铺"
                    if shop:
                        shop.client_id = client_id
                        shop.client_secret_encrypted = app.client_secret_encrypted
                        shop.access_token_encrypted = None
                elif secret_changed and shop:
                    shop.client_secret_encrypted = app.client_secret_encrypted
        session.flush()
        return app

    def authorization(self, session: Session, shop_id: int) -> PddShopAuthorization | None:
        return session.scalar(select(PddShopAuthorization).where(PddShopAuthorization.shop_id == shop_id))

    def start(self, session: Session, shop_id: int) -> tuple[PddAuthorizationSession, str]:
        if session.get(Shop, shop_id) is None:
            raise LookupError("店铺不存在")
        app = self.get_application(session)
        if app is None:
            raise ValueError("请先配置拼多多开放平台应用")
        state = secrets.token_urlsafe(32)
        flow = PddAuthorizationSession(
            state=state,
            shop_id=shop_id,
            application_id=app.id,
            status="pending",
            expires_at=utcnow_naive() + timedelta(minutes=STATE_TTL_MINUTES),
        )
        session.add(flow)
        session.flush()
        url = build_shop_authorization_url(
            client_id=app.client_id,
            redirect_uri=app.redirect_uri,
            state=state,
            auth_web_url=app.auth_web_url,
        )
        return flow, url

    def _app_client(self, app: PddApplication) -> PddClient:
        return self.client_factory(PddCredentials(
            client_id=app.client_id,
            client_secret=self.secret_store.decrypt(app.client_secret_encrypted),
            access_token=None,
        ))

    def complete(self, session: Session, *, state: str, code: str) -> PddShopAuthorization:
        flow = session.scalar(select(PddAuthorizationSession).where(PddAuthorizationSession.state == state))
        if flow is None:
            raise LookupError("授权 state 不存在")
        if flow.status != "pending":
            raise ValueError("该授权流程已经处理")
        if flow.expires_at < utcnow_naive():
            flow.status = "expired"
            raise ValueError("授权流程已过期，请重新发起")
        app = session.get(PddApplication, flow.application_id)
        shop = session.get(Shop, flow.shop_id)
        if app is None or shop is None:
            raise LookupError("授权关联对象不存在")
        payload = self._app_client(app).call("pdd.pop.auth.token.create", {"code": code.strip()})
        token = parse_token_payload(payload)
        auth = self.authorization(session, shop.id)
        if auth is None:
            auth = PddShopAuthorization(shop_id=shop.id, application_id=app.id)
            session.add(auth)
        self._store_token(app, shop, auth, token, refreshed=False)
        flow.status = "completed"
        flow.completed_at = utcnow_naive()
        session.flush()
        return auth

    def _store_token(self, app: PddApplication, shop: Shop, auth: PddShopAuthorization, token: dict[str, Any], *, refreshed: bool) -> None:
        auth.application_id = app.id
        auth.status = "authorized"
        auth.owner_id = token["owner_id"] or auth.owner_id
        auth.owner_name = token["owner_name"] or auth.owner_name
        auth.access_token_encrypted = self.secret_store.encrypt(token["access_token"])
        if token["refresh_token"]:
            auth.refresh_token_encrypted = self.secret_store.encrypt(token["refresh_token"])
        if token["scopes"] or not refreshed:
            auth.scopes_json = json.dumps(token["scopes"], ensure_ascii=False)
        auth.access_expires_at = token["access_expires_at"]
        if token["refresh_expires_at"] is not None or not refreshed:
            auth.refresh_expires_at = token["refresh_expires_at"]
        if refreshed:
            auth.refreshed_at = utcnow_naive()
        else:
            auth.authorized_at = utcnow_naive()
        auth.last_error = None

        # Transitional compatibility mirror for the existing sync/probe engine.
        shop.client_id = app.client_id
        shop.client_secret_encrypted = app.client_secret_encrypted
        shop.access_token_encrypted = auth.access_token_encrypted
        if auth.owner_id:
            shop.owner_id = auth.owner_id

    def refresh(self, session: Session, shop_id: int) -> PddShopAuthorization:
        auth = self.authorization(session, shop_id)
        if auth is None or not auth.refresh_token_encrypted:
            raise ValueError("当前店铺没有可用 refresh_token，请重新授权")
        app = session.get(PddApplication, auth.application_id)
        shop = session.get(Shop, shop_id)
        if app is None or shop is None:
            raise LookupError("授权关联对象不存在")
        refresh_token = self.secret_store.decrypt(auth.refresh_token_encrypted)
        payload = self._app_client(app).call("pdd.pop.auth.token.refresh", {"refresh_token": refresh_token})
        token = parse_token_payload(payload, refresh=True)
        self._store_token(app, shop, auth, token, refreshed=True)
        session.flush()
        return auth

    def disconnect(self, session: Session, shop_id: int) -> None:
        auth = self.authorization(session, shop_id)
        shop = session.get(Shop, shop_id)
        if auth:
            auth.status = "disconnected"
            auth.access_token_encrypted = None
            auth.refresh_token_encrypted = None
            auth.last_error = None
        if shop:
            shop.access_token_encrypted = None
        session.flush()

def authorization_payload(app: PddApplication | None, auth: PddShopAuthorization | None) -> dict[str, Any]:
    scopes: list[str] = []
    if auth and auth.scopes_json:
        try:
            value = json.loads(auth.scopes_json)
            scopes = [str(item) for item in value] if isinstance(value, list) else []
        except json.JSONDecodeError:
            scopes = []
    return {
        "application": None if app is None else {
            "id": app.id,
            "client_id": app.client_id,
            "redirect_uri": app.redirect_uri,
            "has_client_secret": bool(app.client_secret_encrypted),
            "auth_web_url": app.auth_web_url,
            "endpoint_status": app.endpoint_status,
        },
        "authorization": None if auth is None else {
            "status": auth.status,
            "owner_id": auth.owner_id,
            "owner_name": auth.owner_name,
            "scopes": scopes,
            "access_expires_at": auth.access_expires_at.isoformat() if auth.access_expires_at else None,
            "refresh_expires_at": auth.refresh_expires_at.isoformat() if auth.refresh_expires_at else None,
            "authorized_at": auth.authorized_at.isoformat() if auth.authorized_at else None,
            "refreshed_at": auth.refreshed_at.isoformat() if auth.refreshed_at else None,
            "can_refresh": bool(auth.refresh_token_encrypted),
            "last_error": auth.last_error,
        },
    }
