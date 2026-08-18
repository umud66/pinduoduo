import httpx

from app.services.pdd.client import PddClient, PddCredentials


def test_client_parses_success_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        return httpx.Response(200, json={"goods_list_get_response": {"goods_list": []}})

    client = PddClient(
        PddCredentials("client", "secret", "token"),
        gateway_url="https://example.test/api/router",
        transport=httpx.MockTransport(handler),
    )
    response = client.goods_list(page_size=1)
    assert "goods_list_get_response" in response
