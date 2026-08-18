from __future__ import annotations

import os
import sys
from pathlib import Path


def resolve_data_dir(
    *,
    frozen: bool,
    platform_name: str,
    executable: Path,
    home: Path,
    xdg_data_home: str | None = None,
) -> Path:
    """Return the writable default data directory for the current runtime."""

    if not frozen:
        return Path("data")

    if platform_name == "win32":
        return executable.resolve().parent / "data"

    if platform_name == "darwin":
        return home / "Library" / "Application Support" / "PDD AI Operator"

    xdg_root = Path(xdg_data_home).expanduser() if xdg_data_home else home / ".local" / "share"
    return xdg_root / "pdd-ai-operator"


def default_data_dir() -> Path:
    return resolve_data_dir(
        frozen=bool(getattr(sys, "frozen", False)),
        platform_name=sys.platform,
        executable=Path(sys.executable),
        home=Path.home(),
        xdg_data_home=os.getenv("XDG_DATA_HOME"),
    )
