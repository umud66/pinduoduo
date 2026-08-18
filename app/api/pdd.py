from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.pdd.client import PddClient, PddCredentials
from app.services.pdd.probe import PddCapabilityProbe

router = APIRouter(tags=["pdd"])


class PddProbeRequest(BaseModel):
    client_id: str = Field(min_length=1)
    client_secret: str = Field(min_length=1)
    access_token: str | None = None
    gateway_url: str | None = None


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
        report = PddCapabilityProbe(client).run()
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
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
