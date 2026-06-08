#!/usr/bin/env python3
"""
Build branded TikTok photo-carousel frames for each Underdog Goods product.

01-hook navy hook card / 02-tee mockup on cream / 03-design art on mustard
(only when a distinct design exists) / 04-cta clay call-to-action. Frames are
written into the storefront's public/ dir and indexed in social/manifest.json.

Fonts resolve cross-platform via growth.fonts (Liberation on Linux runners,
Arial on macOS). Run with the repo root on PYTHONPATH.

  build_carousels.py                 # all products
  build_carousels.py --product professional-napper-tee
"""
import argparse
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from growth.fonts import resolve_font  # noqa: E402

WEB = os.environ.get("UNDERDOG_WEB", "/Users/Claude/Desktop/Pandora/projects/underdog-goods-web")
PRODUCTS = os.path.join(WEB, "data", "products.json")
PUBLIC = os.path.join(WEB, "public")
OUT_ROOT = os.path.join(PUBLIC, "social")

W, H = 1080, 1920  # TikTok-native vertical

INK = (46, 49, 146)
CREAM = (246, 239, 224)
CLAY = (224, 122, 95)
MUSTARD = (229, 178, 93)
TEXT = (27, 27, 47)

EMOJI_RE = re.compile(
    "[" "\U0001F000-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F1E6-\U0001F1FF"
    "\U0000FE00-\U0000FE0F" "\U00002190-\U000021FF" "\U00002B00-\U00002BFF" "]+",
    flags=re.UNICODE,
)

# Fallback hooks for the original 7 (a brief-driven design injects its own via _hook).
HOOKS = {
    "professional-napper-tee": "POV: your dog has a full-time job and it is napping",
    "good-boy-club-tee": "Whole personality? It is the dog. Welcome to the Good Boy Club",
    "snack-goblin-tee": "Sweet, innocent, and four seconds from your sandwich",
    "anti-social-pro-nap-tee": "Cancel the plans. The couch needs us",
    "will-work-for-treats-tee": "Loyal. Hireable. Motivated entirely by snacks",
    "my-whole-heart-tee": "Some dogs fetch the ball. Yours fetched your whole heart",
    "adopt-love-repeat-tee": "Adopt. Love. Repeat. The only program that actually sticks",
}


def font(bold, size):
    return ImageFont.truetype(resolve_font(bold=bold), size)


def theme_hook(slug):
    """Carousel hook for auto-generated designs, read from the growth-side themes.json."""
    path = os.environ.get("UNDERDOG_THEMES")
    if path and os.path.exists(path):
        try:
            return (json.load(open(path)).get(slug) or {}).get("tt_hook")
        except Exception:
            return None
    return None


def clean(s):
    return EMOJI_RE.sub("", s or "").replace("  ", " ").strip()


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_block(draw, lines, fnt, color, cx, top, line_gap=1.18, center=True):
    y = top
    for ln in lines:
        w = draw.textlength(ln, font=fnt)
        x = cx - w / 2 if center else cx
        draw.text((x, y), ln, font=fnt, fill=color)
        y += int(fnt.size * line_gap)
    return y


def fit_paste(canvas, img_path, box_w, box_h, cx, cy, bg=None):
    img = Image.open(img_path).convert("RGBA")
    img.thumbnail((box_w, box_h), Image.LANCZOS)
    x = int(cx - img.width / 2)
    y = int(cy - img.height / 2)
    if bg is not None:
        plate = Image.new("RGBA", img.size, bg + (255,))
        plate.alpha_composite(img)
        img = plate
    canvas.alpha_composite(img, (x, y))


def card(bg):
    c = Image.new("RGBA", (W, H), bg + (255,))
    return c, ImageDraw.Draw(c)


def frame_hook(slug, hook):
    c, d = card(INK)
    d.text((80, 110), "UNDERDOG GOODS", font=font(True, 40), fill=CREAM)
    d.line((80, 175, 360, 175), fill=MUSTARD, width=6)
    h = clean(hook).upper()
    f = font(True, 96)
    lines = wrap(d, h, f, W - 160)
    while len(lines) > 5 and f.size > 60:
        f = font(True, f.size - 6)
        lines = wrap(d, h, f, W - 160)
    total = len(lines) * int(f.size * 1.12)
    draw_block(d, lines, f, CREAM, W // 2, (H - total) // 2 - 60)
    d.text((W // 2 - d.textlength("SWIPE TO SHOP  >", font=font(True, 44)) / 2, H - 230),
           "SWIPE TO SHOP  >", font=font(True, 44), fill=MUSTARD)
    return c


def frame_tee(product, mockup):
    c, d = card(CREAM)
    fit_paste(c, mockup, 900, 1180, W // 2, 760)
    name = product["name"].replace(" Tee", "").upper()
    d.text((W // 2 - d.textlength(name, font=font(True, 64)) / 2, 1560),
           name, font=font(True, 64), fill=TEXT)
    price = "$%.2f  ·  printed to order" % product.get("price_usd", 19.99)
    d.text((W // 2 - d.textlength(price, font=font(False, 40)) / 2, 1660),
           price, font=font(False, 40), fill=CLAY)
    return c


def frame_design(design):
    c, d = card(MUSTARD)
    d.text((80, 120), "THE DESIGN", font=font(True, 56), fill=TEXT)
    fit_paste(c, design, 880, 1180, W // 2, 1000)
    return c


def frame_cta():
    c, d = card(CLAY)
    f1 = font(True, 70)
    for i, ln in enumerate(["ORIGINAL TEES", "FOR DOG PEOPLE"]):
        d.text((W // 2 - d.textlength(ln, font=f1) / 2, 520 + i * 92), ln, font=f1, fill=CREAM)
    big = font(True, 120)
    d.text((W // 2 - d.textlength("LINK IN BIO", font=big) / 2, 880), "LINK IN BIO", font=big, fill=CREAM)
    d.text((W // 2 - d.textlength("@underdoggoods", font=font(False, 54)) / 2, 1080),
           "@underdoggoods", font=font(False, 54), fill=CREAM)
    d.text((W // 2 - d.textlength("made to order  ·  join the waitlist", font=font(False, 40)) / 2, 1180),
           "made to order  ·  join the waitlist", font=font(False, 40), fill=(255, 255, 255))
    return c


def resolve_sources(p):
    mock = os.path.join(PUBLIC, p["mockup"].lstrip("/"))
    design = None
    dp = p.get("design")
    if dp and dp != p["mockup"]:
        cand = os.path.join(PUBLIC, dp.lstrip("/"))
        if os.path.exists(cand):
            design = cand
    if not design:
        base = p["slug"].replace("-tee", "")
        cand = os.path.join(PUBLIC, "product-shots", base + ".png")
        if os.path.exists(cand) and os.path.abspath(cand) != os.path.abspath(mock):
            design = cand
    return mock, design


def build(p):
    slug = p["slug"]
    out = os.path.join(OUT_ROOT, slug)
    os.makedirs(out, exist_ok=True)
    mock, design = resolve_sources(p)
    frames = []

    def save(name, img):
        path = os.path.join(out, name)
        img.convert("RGB").save(path, "PNG")
        frames.append("/social/%s/%s" % (slug, name))

    hook = theme_hook(slug) or HOOKS.get(slug) or p.get("headline", p["name"])
    save("01-hook.png", frame_hook(slug, hook))
    save("02-tee.png", frame_tee(p, mock))
    if design:
        save("03-design.png", frame_design(design))
    save("04-cta.png", frame_cta())
    return slug, frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product")
    args = ap.parse_args()
    data = json.load(open(PRODUCTS))
    products = data if isinstance(data, list) else data.get("products", data)
    if args.product:
        products = [x for x in products if x["slug"] == args.product] or sys.exit("no such product")

    os.makedirs(OUT_ROOT, exist_ok=True)
    manifest_path = os.path.join(OUT_ROOT, "manifest.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}

    for p in products:
        slug, frames = build(p)
        manifest[slug] = frames
        print("  %-26s %d frames" % (slug, len(frames)))

    json.dump(manifest, open(manifest_path, "w"), indent=2)
    print("manifest -> %s" % manifest_path)


if __name__ == "__main__":
    main()
