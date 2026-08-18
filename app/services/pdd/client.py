from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Mapping

import httpx

from app.core.config import get_settings


class PddApiError(RuntimeError):
    def __init__(self, message: str, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.payload = payload or {}


def build_sign(client_secret: str, params: Mapping[str, Any]) -> str:
    """Build the classic PDD Open Platform request signature.

    The gateway and signing behavior are isolated here intentionally. If PDD changes
    the authentication mechanism for a specific application type, only this adapter
    should need to change.
    """

    chunks = [client_secret]
    for key in sorted(params):
        value = params[key]
        if value is None:
            continue
        chunks.append(f"{key}{value}")
    chunks.append(client_secret)
    return hashlib.md5("".join(chunks).encode("utf-8")).hexdigest().upper()


@dataclass(slots=True)
class PddCredentials:
    client_id: str
    client_secret: str
    access_token: str | None = None


class PddClient:
    def __init__(
        self,
        credentials: PddCredentials,
        *,
        gateway_url: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.credentials = credentials
        self.gateway_url = gateway_url or settings.pdd_gateway_url
        self.timeout_seconds = timeout_seconds or settings.request_timeout_seconds
        self.transport = transport

    def build_params(self, api_type: str, business_params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {
            "type": api_type,
            "client_id": self.credentials.client_id,
            "timestamp": int(time.time()),
            "data_type": "JSON",
        }
        if self.credentials.access_token:
            params["access_token"] = self.credentials.access_token
        for key, value in (business_params or {}).items():
            if value is not None:
                if isinstance(value, (dict, list, tuple)):
                    params[key] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                else:
                    params[key] = value
        params["sign"] = build_sign(self.credentials.client_secret, params)
        return params

    def call(self, api_type: str, business_params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        params = self.build_params(api_type, business_params)
        with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
            response = client.post(self.gateway_url, data=params)
            response.raise_for_status()
            payload = response.json()
        if isinstance(payload, dict) and payload.get("error_response"):
            error = payload["error_response"]
            message = str(error.get("error_msg") or error.get("sub_msg") or "PDD API error")
            raise PddApiError(message, payload=payload)
        if not isinstance(payload, dict):
            raise PddApiError("PDD API returned a non-object response", payload={"raw": payload})
        return payload

    def goods_list(self, *, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        return self.call("pdd.goods.list.get", {"page": page, "page_size": page_size})

    def goods_detail(self, goods_id: int | str) -> dict[str, Any]:
        return self.call("pdd.goods.detail.get", {"goods_id": goods_id})

    def order_increment(
        self,
        *,
        start_updated_at: int,
        end_updated_at: int,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return self.call(
            "pdd.order.number.list.increment.get",
            {
                "start_updated_at": start_updated_at,
                "end_updated_at": end_updated_at,
                "page": page,
                "page_size": page_size,
            },
        )

    def refund_increment(
        self,
        *,
        start_updated_at: int,
        end_updated_at: int,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return self.call(
            "pdd.refund.list.increment.get",
            {
                "start_updated_at": start_updated_at,
                "end_updated_at": end_updated_at,
                "page": page,
                "page_size": page_size,
            },
        )
