from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class SecretStore:
    """Local-at-rest encryption for API credentials.

    This protects against accidental plaintext exposure in SQLite/logs. It is not a
    substitute for OS account security because the key necessarily lives on the same
    single-user machine in the one-click deployment model.
    """

    def __init__(self, key_path: Path | None = None) -> None:
        settings = get_settings()
        self.key_path = key_path or (settings.data_dir / "secret.key")
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(self._load_or_create_key())

    def _load_or_create_key(self) -> bytes:
        if self.key_path.exists():
            return self.key_path.read_bytes().strip()
        key = Fernet.generate_key()
        self.key_path.write_bytes(key)
        return key

    def encrypt(self, value: str) -> str:
        if not value:
            return ""
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        if not value:
            return ""
        try:
            return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("无法解密本地密钥；secret.key 可能与数据库不匹配") from exc
