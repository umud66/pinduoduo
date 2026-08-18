from pathlib import Path

from app.core.paths import resolve_data_dir


def test_source_runtime_uses_project_data_directory() -> None:
    result = resolve_data_dir(
        frozen=False,
        platform_name="linux",
        executable=Path("/tmp/app"),
        home=Path("/home/test"),
    )
    assert result == Path("data")


def test_windows_release_keeps_data_next_to_executable() -> None:
    result = resolve_data_dir(
        frozen=True,
        platform_name="win32",
        executable=Path("C:/PDD/PDD运营助手.exe"),
        home=Path("C:/Users/test"),
    )
    assert result.as_posix().endswith("PDD/data")


def test_macos_release_uses_application_support() -> None:
    result = resolve_data_dir(
        frozen=True,
        platform_name="darwin",
        executable=Path("/Applications/PDD运营助手.app/Contents/MacOS/PDD运营助手"),
        home=Path("/Users/test"),
    )
    assert result == Path("/Users/test/Library/Application Support/PDD AI Operator")


def test_linux_release_respects_xdg_data_home() -> None:
    result = resolve_data_dir(
        frozen=True,
        platform_name="linux",
        executable=Path("/opt/pdd/PDD-AI-Operator"),
        home=Path("/home/test"),
        xdg_data_home="/srv/user-data",
    )
    assert result == Path("/srv/user-data/pdd-ai-operator")
