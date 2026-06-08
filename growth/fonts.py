"""Cross-platform font resolution for the carousel builder.

Order: env override -> repo-vendored TTF -> Linux Liberation (apt) -> macOS Arial.
build_carousels.wrap() measures the actual font, so any sans font is layout-safe.
"""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_VENDOR = os.path.join(os.path.dirname(_HERE), "assets", "fonts")

_CANDIDATES = {
    True: (
        "UNDERDOG_FONT_BOLD",
        ["LiberationSans-Bold.ttf"],
        [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ],
    ),
    False: (
        "UNDERDOG_FONT_REG",
        ["LiberationSans-Regular.ttf"],
        [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ],
    ),
}


def resolve_font(bold=True):
    env, vendored, system = _CANDIDATES[bool(bold)]
    val = os.environ.get(env)
    if val and os.path.exists(val):
        return val
    for name in vendored:
        p = os.path.join(_VENDOR, name)
        if os.path.exists(p):
            return p
    for p in system:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"no usable font found for bold={bold}")
