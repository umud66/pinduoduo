import httpx

from app.services.pdd.client import PddClient, PddCredentials
from app.services.pdd.runner import _result_has_changes


def test_client_retries_transient_http_error(monkeypatch) -> None:
    attempts = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(503, json={"message": "busy"})
        return httpx.Response(200, json={"goods_list_get_response": {"goods_list": []}})

    monkeypatch.setattr("app.services.pdd.client.time.sleep", lambda _seconds: None)
    client = PddClient(
        PddCredentials("client", "secret", "token"),
        gateway_url="https://example.test/api/router",
        transport=httpx.MockTransport(handler),
        max_attempts=2,
    )

    response = client.goods_list(page_size=1)

    assert attempts["count"] == 2
    assert "goods_list_get_response" in response


def test_sync_result_change_detection() -> None:
    assert _result_has_changes({"orders": {"created": 1}}) is True
    assert _result_has_changes({"orders": 0, "refunds": {"updated": 0}}) is False
