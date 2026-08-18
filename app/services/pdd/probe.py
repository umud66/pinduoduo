from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from app.services.pdd.client import PddApiError, PddClient


@dataclass(slots=True)
class ProbeItem:
    api_type: str
    status: str
    message: str
    response_keys: list[str]


@dataclass(slots=True)
class ProbeReport:
    checked_at: int
    items: list[ProbeItem]

    @property
    def summary(self) -> dict[str, int]:
        result = {"ok": 0, "denied": 0, "error": 0}
        for item in self.items:
            result[item.status] = result.get(item.status, 0) + 1
        return result


class PddCapabilityProbe:
    """Probe only low-volume read capabilities.

    The probe is intentionally conservative: it does not mutate shop data and does
    not assume traffic/ad scopes exist. A permission error is recorded as `denied`
    rather than treated as an application crash.
    """

    def __init__(self, client: PddClient) -> None:
        self.client = client

    def run(self) -> ProbeReport:
        now = int(time.time())
        one_hour_ago = now - 3600
        checks: list[tuple[str, Callable[[], dict[str, Any]]]] = [
            ("pdd.goods.list.get", lambda: self.client.goods_list(page=1, page_size=1)),
            (
                "pdd.order.number.list.increment.get",
                lambda: self.client.order_increment(
                    start_updated_at=one_hour_ago, end_updated_at=now, page=1, page_size=1
                ),
            ),
            (
                "pdd.refund.list.increment.get",
                lambda: self.client.refund_increment(
                    start_updated_at=one_hour_ago, end_updated_at=now, page=1, page_size=1
                ),
            ),
        ]

        items: list[ProbeItem] = []
        for api_type, check in checks:
            try:
                payload = check()
                items.append(
                    ProbeItem(
                        api_type=api_type,
                        status="ok",
                        message="调用成功",
                        response_keys=sorted(payload.keys()),
                    )
                )
            except PddApiError as exc:
                text = str(exc)
                status = "denied" if any(k in text.lower() for k in ("权限", "scope", "access", "授权")) else "error"
                items.append(
                    ProbeItem(api_type=api_type, status=status, message=text, response_keys=[])
                )
            except Exception as exc:
                items.append(
                    ProbeItem(api_type=api_type, status="error", message=str(exc), response_keys=[])
                )
        return ProbeReport(checked_at=now, items=items)
