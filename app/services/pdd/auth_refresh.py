from __future__ import annotations

import threading
from sqlalchemy import select

from app.db.database import session_scope
from app.db.models import Shop
from app.db.pdd_auth_models import PddShopAuthorization
from app.services.pdd.auth import PddAuthorizationService
from app.services.pdd.auth_lifecycle import token_refresh_action
from app.services.pdd.auth_protocol import utcnow_naive

class PddTokenRefreshScheduler:
    def __init__(self, poll_seconds: int = 300) -> None:
        self.poll_seconds = poll_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.service = PddAuthorizationService()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="pdd-token-refresh", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _loop(self) -> None:
        while not self._stop.wait(self.poll_seconds):
            try:
                self._tick()
            except Exception:
                continue

    def _tick(self) -> None:
        now = utcnow_naive()
        candidates: list[int] = []
        with session_scope() as session:
            rows = session.scalars(
                select(PddShopAuthorization).where(PddShopAuthorization.status == "authorized")
            ).all()
            for auth in rows:
                action = token_refresh_action(
                    now=now,
                    access_expires_at=auth.access_expires_at,
                    refresh_expires_at=auth.refresh_expires_at,
                    has_refresh_token=bool(auth.refresh_token_encrypted),
                )
                if action == "refresh":
                    candidates.append(auth.shop_id)
                elif action == "reauthorize":
                    auth.status = "expired"
                    auth.last_error = "授权凭证已过期，请重新绑定拼多多店铺"
                    shop = session.get(Shop, auth.shop_id)
                    if shop:
                        shop.access_token_encrypted = None

        for shop_id in candidates:
            try:
                with session_scope() as session:
                    self.service.refresh(session, shop_id)
            except Exception as exc:
                with session_scope() as session:
                    auth = self.service.authorization(session, shop_id)
                    if auth:
                        auth.status = "refresh_failed"
                        auth.last_error = str(exc)
                        shop = session.get(Shop, auth.shop_id)
                        if shop:
                            shop.access_token_encrypted = None

pdd_token_refresh_scheduler = PddTokenRefreshScheduler()
