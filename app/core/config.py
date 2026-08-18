from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "拼多多 AI 运营助手"
    host: str = "127.0.0.1"
    port: int = 8765
    debug: bool = False
    auto_open_browser: bool = True

    data_dir: Path = Field(default=Path("data"))
    database_filename: str = "app.db"
    pdd_gateway_url: str = "https://gw-api.pinduoduo.com/api/router"
    request_timeout_seconds: float = 30.0

    model_config = SettingsConfigDict(
        env_prefix="PDD_AI_",
        env_file=".env",
        extra="ignore",
    )

    @property
    def database_path(self) -> Path:
        return self.data_dir / self.database_filename

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"

    def ensure_directories(self) -> None:
        for name in ("", "imports", "images", "backups"):
            (self.data_dir / name).mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
