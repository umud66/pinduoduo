from app.services.pdd.client import build_sign


def test_sign_is_sorted_and_uppercase() -> None:
    params_a = {"type": "demo.api", "client_id": "abc", "timestamp": 123}
    params_b = {"timestamp": 123, "client_id": "abc", "type": "demo.api"}

    sign_a = build_sign("secret", params_a)
    sign_b = build_sign("secret", params_b)

    assert sign_a == sign_b
    assert sign_a == sign_a.upper()
    assert len(sign_a) == 32
