import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from growth import fonts  # noqa: E402


def test_resolve_returns_existing_ttf():
    p = fonts.resolve_font(bold=True)
    assert os.path.exists(p)
    assert p.lower().endswith(".ttf")


def test_resolve_regular():
    p = fonts.resolve_font(bold=False)
    assert os.path.exists(p)


def test_env_override(tmp_path, monkeypatch):
    f = tmp_path / "x.ttf"
    f.write_bytes(b"\x00")
    monkeypatch.setenv("UNDERDOG_FONT_BOLD", str(f))
    assert fonts.resolve_font(bold=True) == str(f)
