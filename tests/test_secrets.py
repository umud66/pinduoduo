from pathlib import Path

from app.core.secrets import SecretStore


def test_secret_store_roundtrip(tmp_path: Path) -> None:
    store = SecretStore(tmp_path / "secret.key")
    encrypted = store.encrypt("sk-example")
    assert encrypted != "sk-example"
    assert store.decrypt(encrypted) == "sk-example"
