from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.secrets import SecretStore
from app.db.database import session_scope
from app.db.models import Shop
from app.services.pdd.client import PddClient, PddCredentials
from app.services.pdd.probe import PddCapabilityProbe

router = APIRouter(tags=["pdd"])
secret_store = SecretStore()


class PddProbeRequest(BaseModel):
    client_id: str = Field(min_length=1)
    client_secret: str = Field(min_length=1)
    access_token: str | None = None
    gateway_url: str | None = None


def _report_payload(report) -> dict[str, object]:
    return {
        "checked_at": report.checked_at,
        "summary": report.summary,
        "items": [
            {
                "api_type": item.api_type,
                "status": item.status,
                "message": item.message,
                "response_keys": item.response_keys,
            }
            for item in report.items
        ],
    }


@router.post("/pdd/probe")
def probe_pdd(payload: PddProbeRequest) -> dict[str, object]:
    try:
        client = PddClient(
            PddCredentials(
                client_id=payload.client_id,
                client_secret=payload.client_secret,
                access_token=payload.access_token,
            ),
            gateway_url=payload.gateway_url,
        )
        return _report_payload(PddCapabilityProbe(client).run())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pdd/shops/{shop_id}/probe")
def probe_saved_shop(shop_id: int) -> dict[str, object]:
    with session_scope() as session:
        shop = session.get(Shop, shop_id)
        if shop is None:
            raise HTTPException(status_code=404, detail="店铺不存在")
        if not shop.client_id or not shop.client_secret_encrypted:
            raise HTTPException(status_code=400, detail="请先在设置中填写 Client ID 和 Client Secret")
        try:
            credentials = PddCredentials(
                client_id=shop.client_id,
                client_secret=secret_store.decrypt(shop.client_secret_encrypted),
                access_token=secret_store.decrypt(shop.access_token_encrypted or "") or None,
            )
            return _report_payload(PddCapabilityProbe(PddClient(credentials)).run())
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
