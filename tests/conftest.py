from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA = ROOT / "tests" / "data"


@pytest.fixture(scope="session")
def data_dir() -> Path:
    if not (DATA / "mixed.txt").exists():  # regenerate on demand
        from tests.make_fixtures import main as make

        make()
    return DATA


@pytest.fixture(scope="session")
def mixed_text(data_dir: Path) -> str:
    return (data_dir / "mixed.txt").read_text(encoding="utf-8")


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> Path:
    """Run inside a throwaway directory so nothing is written into the repo."""

    monkeypatch.chdir(tmp_path)
    # mirror the repo layout the pipeline expects at runtime
    (tmp_path / "links.txt").write_text((ROOT / "links.txt").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "# test\n\n<!-- POPVPN:STATS:START -->\nold\n<!-- POPVPN:STATS:END -->\n\ntail\n",
        encoding="utf-8",
    )
    return tmp_path
