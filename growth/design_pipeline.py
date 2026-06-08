"""Parameterized image pipeline: Recraft render -> transparent prep -> tee composite.

Extracted from the Mac-only one-off scripts (generate_design_batch / prep /
composite) into single-design, brief-driven functions with no hardcoded paths.
Writes product-shots into the given web checkout (the cloned walnut repo).
"""
import io
import json
import os
import urllib.request
import urllib.error

from PIL import Image

RECRAFT_URL = "https://external.api.recraft.ai/v1/images/generations"
HERE = os.path.dirname(os.path.abspath(__file__))
BLANK_TEE = os.path.join(os.path.dirname(HERE), "assets", "blank-tee.png")
CANVAS = (1024, 1365)
# chest print box on the 1024x1024 blank tee (center x, center y, max w, max h)
BOX_CX, BOX_CY, BOX_W, BOX_H = 508, 470, 330, 400


def recraft_generate(prompt):
    key = os.environ.get("RECRAFT_API_KEY")
    if not key:
        raise SystemExit("RECRAFT_API_KEY not set")
    body = json.dumps({
        "prompt": prompt, "style": "digital_illustration",
        "model": "recraftv3", "size": "1024x1365", "n": 1, "response_format": "url",
    }).encode()
    # Recraft sits behind Cloudflare, which 403s the default urllib User-Agent
    # (error 1010 = banned signature). Send a normal browser UA.
    UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    req = urllib.request.Request(RECRAFT_URL, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", UA)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            url = json.loads(r.read().decode())["data"][0]["url"]
        img_req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(img_req, timeout=180) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Recraft HTTP {e.code}: {e.read().decode()[:300]}")


def _corners_white(img, n=24, thresh=244):
    g = img.convert("L")
    w, h = g.size
    boxes = [(0, 0, n, n), (w - n, 0, w, n), (0, h - n, n, h), (w - n, h - n, w, h)]
    return all(sum(g.crop(b).getdata()) / (n * n) >= thresh for b in boxes)


def _white_to_transparent(img):
    alpha = img.convert("L").point(lambda p: 0 if p >= 246 else 255)
    out = img.convert("RGBA")
    out.putalpha(alpha)
    return out


def prep_transparent(png_bytes):
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    if _corners_white(img):
        img = _white_to_transparent(img)
    tw, th = CANVAS
    s = min(tw / img.width, th / img.height)
    nw, nh = max(1, round(img.width * s)), max(1, round(img.height * s))
    r = img.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    canvas.alpha_composite(r, ((tw - nw) // 2, (th - nh) // 2))
    return canvas


def composite_on_tee(design_img):
    tee = Image.open(BLANK_TEE).convert("RGBA")
    art = design_img
    bbox = art.getchannel("A").getbbox()
    if bbox:
        art = art.crop(bbox)
    s = min(BOX_W / art.width, BOX_H / art.height)
    nw, nh = max(1, round(art.width * s)), max(1, round(art.height * s))
    art = art.resize((nw, nh), Image.Resampling.LANCZOS)
    tee.alpha_composite(art, (BOX_CX - nw // 2, BOX_CY - nh // 2))
    return tee


def render(slug, prompt, web_dir):
    """Generate + prep + composite. Returns the storefront paths + local mockup path."""
    shots = os.path.join(web_dir, "public", "product-shots")
    os.makedirs(shots, exist_ok=True)
    design = prep_transparent(recraft_generate(prompt))
    design.save(os.path.join(shots, f"{slug}.png"))
    mock_path = os.path.join(shots, f"{slug}-tee.png")
    composite_on_tee(design).convert("RGB").save(mock_path)
    return {
        "design": f"/product-shots/{slug}.png",
        "mockup": f"/product-shots/{slug}-tee.png",
        "mockup_path": mock_path,
    }
