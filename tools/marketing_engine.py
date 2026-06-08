#!/usr/bin/env python3
"""
Underdog Goods — social marketing engine.

Generates PLATFORM-FITTED posts for each product and pushes them to Zernio.
TikTok and Pinterest reward very different content, so the engine produces
different copy per platform on purpose:

  TikTok    photo post. Hook-first, casual, trend-aware, emoji, broad + niche
            hashtags. Links are NOT clickable in TikTok captions, so the CTA is
            "link in bio". Goal: reach / virality.

  Pinterest pin. Pinterest is a SEARCH ENGINE, not a feed: SEO title +
            keyword-rich description + a destination link that drives traffic.
            Pins live 3-6 months. Requires a board. Goal: evergreen storefront
            clicks (the demand-test signal).

Default mode is DRAFT (review gate) — nothing publishes without sign-off.

Usage:
  # preview the copy without touching Zernio
  marketing_engine.py --product professional-napper-tee --platforms tiktok,pinterest --preview

  # create drafts (default mode)
  marketing_engine.py --product professional-napper-tee --platforms tiktok,pinterest

  # every product, drafts
  marketing_engine.py --all --platforms tiktok,pinterest

  # schedule instead of draft
  marketing_engine.py --product good-boy-club-tee --platforms pinterest --mode schedule --at 2026-06-05T16:00:00

Env (all have sane defaults):
  ZERNIO_API_KEY            (required — read from .env)
  ZERNIO_PROFILE_ID         default 6a1f7e7f5764bf632edb335e
  ZERNIO_TIKTOK_ACCOUNT     default 6a20c2af2b2567671abcb513
  ZERNIO_PINTEREST_ACCOUNT  default 6a20c3322b2567671abcbb77
  ZERNIO_PINTEREST_BOARD    Pinterest board id (required for Pinterest posts)
  SITE_BASE                 default https://underdog-goods.vercel.app
  UNDERDOG_PRODUCTS         path to the storefront products.json
"""
import argparse
import datetime
import json
import os
import sys
import urllib.request
import urllib.error

# attribution ledger: post_id -> {slug, platform, mode} so the growth loop can
# join Zernio analytics back to the design that produced the post.
LEDGER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "growth", "state", "posts.json")


def ledger_append(post_id, slug, platform, mode):
    try:
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        data = json.load(open(LEDGER)) if os.path.exists(LEDGER) else {}
        data[post_id] = {
            "slug": slug, "platform": platform, "mode": mode,
            "created": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        json.dump(data, open(LEDGER, "w"), indent=2)
    except Exception as e:
        print(f"  (ledger write skipped: {e})")

ZERNIO_BASE = "https://zernio.com/api/v1"
SITE_BASE = os.environ.get("SITE_BASE", "https://underdog-goods.vercel.app").rstrip("/")
PROFILE_ID = os.environ.get("ZERNIO_PROFILE_ID", "6a1f7e7f5764bf632edb335e")
ACCOUNTS = {
    "tiktok": os.environ.get("ZERNIO_TIKTOK_ACCOUNT", "6a20c2af2b2567671abcb513"),
    "pinterest": os.environ.get("ZERNIO_PINTEREST_ACCOUNT", "6a20c3322b2567671abcbb77"),
}
PINTEREST_BOARD = os.environ.get("ZERNIO_PINTEREST_BOARD", "")
WEB_DATA = os.environ.get(
    "UNDERDOG_PRODUCTS",
    "/Users/Claude/Desktop/Pandora/projects/underdog-goods-web/data/products.json",
)
# carousel frame manifest written by tools/build_carousels.py (slug -> [/social/.../NN.png])
WEB_ROOT = os.path.dirname(os.path.dirname(WEB_DATA))
MANIFEST = os.environ.get("UNDERDOG_MANIFEST", os.path.join(WEB_ROOT, "public", "social", "manifest.json"))
API_KEY = os.environ.get("ZERNIO_API_KEY", "")

_MANIFEST_CACHE = None


def carousel_frames(p):
    """Hosted URLs for a product's TikTok carousel frames. Falls back to the
    single mockup if no carousel has been generated yet."""
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is None:
        _MANIFEST_CACHE = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    paths = _MANIFEST_CACHE.get(p["slug"])
    if not paths:
        return [mockup_url(p)]
    return [SITE_BASE + path for path in paths]

# ---------------------------------------------------------------------------
# Content layer — curated, platform-fitted copy per product.
# Brand voice: warm, funny, plain. No em dashes.
# ---------------------------------------------------------------------------
TIKTOK_CORE_TAGS = [
    "#dogsoftiktok", "#dogmom", "#dogdad", "#doglover",
    "#petsoftiktok", "#dogtok", "#fyp",
]

THEMES = {
    "professional-napper-tee": {
        "tt_hook": "POV: your dog has a full-time job and it is napping 😴",
        "tt_tags": ["#frenchbulldog", "#lazydog", "#napqueen", "#introvertlife"],
        "pin_title": "Professional Napper Dog T-Shirt | Funny Sleepy French Bulldog Tee",
        "pin_keywords": "funny dog t-shirt, French Bulldog gift, lazy dog tee, dog mom shirt, introvert gift, sleepy dog",
        "audience": "dog moms, dog dads, introverts, and proud homebodies",
    },
    "good-boy-club-tee": {
        "tt_hook": "Whole personality? It is the dog. Welcome to the Good Boy Club 🐾",
        "tt_tags": ["#goodboy", "#vintagetee", "#dogpeople", "#puppylove"],
        "pin_title": "Good Boy Club T-Shirt | Funny Vintage Dog Lover Tee and Gift",
        "pin_keywords": "good boy shirt, vintage dog tee, dog lover gift, retro dog badge, dog mom shirt",
        "audience": "people whose entire personality is their dog",
    },
    "snack-goblin-tee": {
        "tt_hook": "Sweet, innocent, and four seconds from your sandwich 👀",
        "tt_tags": ["#snackgoblin", "#foodmotivated", "#naughtydog", "#doghumor"],
        "pin_title": "Snack Goblin Dog T-Shirt | Funny Food Motivated Dog Lover Tee",
        "pin_keywords": "funny dog shirt, food motivated dog, snack thief tee, dog humor gift, dog lover shirt",
        "audience": "owners of a small, food-obsessed gremlin",
    },
    "anti-social-pro-nap-tee": {
        "tt_hook": "Cancel the plans. The couch needs us 🛋️",
        "tt_tags": ["#antisocial", "#homebody", "#lazysunday", "#couchpotato"],
        "pin_title": "Anti-Social Pro-Nap Dog T-Shirt | Funny Homebody Dog Lover Tee",
        "pin_keywords": "homebody shirt, funny dog tee, introvert gift, lazy day shirt, dog mom gift",
        "audience": "homebodies, introverts, and plan-cancelers",
    },
    "will-work-for-treats-tee": {
        "tt_hook": "Loyal. Hireable. Motivated entirely by snacks 🦴",
        "tt_tags": ["#dogtreats", "#foodmotivated", "#goodboy", "#trainingtreats"],
        "pin_title": "Will Work For Treats Dog T-Shirt | Funny Dog Lover Tee and Gift",
        "pin_keywords": "funny dog shirt, dog treats tee, food motivated dog, dog trainer gift, dog lover shirt",
        "audience": "owners of a very good, very food-motivated employee of the month",
    },
    "my-whole-heart-tee": {
        "tt_hook": "Some dogs fetch the ball. Yours fetched your whole heart 🤍",
        "tt_tags": ["#dogmomlife", "#puppylove", "#rescuedog", "#myheart"],
        "pin_title": "My Whole Heart Dog T-Shirt | Cute Dog Mom Tee and Gift",
        "pin_keywords": "cute dog shirt, dog mom gift, dog love tee, paw heart shirt, sentimental dog gift",
        "audience": "the unashamedly sappy dog people",
    },
    "adopt-love-repeat-tee": {
        "tt_hook": "Adopt. Love. Repeat. The only program that actually sticks 🐕",
        "tt_tags": ["#adoptdontshop", "#rescuedog", "#mutts", "#rescuedismyfavoritebreed"],
        "pin_title": "Adopt Love Repeat T-Shirt | Dog Rescue and Adoption Lover Tee",
        "pin_keywords": "rescue dog shirt, adopt dont shop tee, dog adoption gift, mutt lover shirt, rescue mom gift",
        "audience": "rescue people and the scruffy, perfect mutts who rescued them back",
    },
}


def load_products():
    d = json.load(open(WEB_DATA))
    return d if isinstance(d, list) else d.get("products", d)


def get_product(slug):
    for p in load_products():
        if p["slug"] == slug:
            return p
    sys.exit(f"product not found: {slug}\navailable: " + ", ".join(p['slug'] for p in load_products()))


def mockup_url(p):
    return SITE_BASE + p["mockup"]


def page_url(p):
    return f"{SITE_BASE}/product/{p['slug']}"


def _load_themes():
    """Hardcoded THEMES for the original catalog, overlaid with growth-side themes.json
    (where the autonomous brief author writes social copy for new designs)."""
    merged = dict(THEMES)
    path = os.environ.get("UNDERDOG_THEMES", os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "growth", "state", "themes.json"))
    if os.path.exists(path):
        try:
            merged.update(json.load(open(path)))
        except Exception:
            pass
    return merged


def theme(p):
    return _load_themes().get(p["slug"], {})


def tiktok_caption(p):
    t = theme(p)
    hook = t.get("tt_hook") or p.get("headline") or p["name"]
    tags = TIKTOK_CORE_TAGS + t.get("tt_tags", [])
    body = (
        f"{hook}\n\n"
        f"{p.get('blurb', '')}\n"
        f"Made to order, printed when you order it. Tag your good dog 🐾\n"
        f"Grab yours 👉 link in bio 👇\n\n"
        + " ".join(tags)
    )
    return body[:2200]


# TikTok PHOTO (slideshow) posts use the caption as the slideshow *title*, which
# TikTok caps at 90 chars — so a photo carousel can't carry the long video-style
# caption above. Lead with the hook (the CTA + storefront link live in the bio and
# on the final carousel frame); add a couple broad tags only if they fit.
TIKTOK_PHOTO_TITLE_MAX = 90


def tiktok_photo_title(p):
    t = theme(p)
    title = (t.get("tt_hook") or p.get("headline") or p["name"]).strip()
    for tag in ("#dogsoftiktok", "#fyp"):
        if len(title) + 1 + len(tag) <= TIKTOK_PHOTO_TITLE_MAX:
            title += " " + tag
    return title[:TIKTOK_PHOTO_TITLE_MAX]


def pinterest_pin(p):
    t = theme(p)
    title = (t.get("pin_title") or f"{p['name']} | Funny Dog Lover T-Shirt")[:100]
    kw = t.get("pin_keywords", "funny dog t-shirt, dog lover gift, dog mom shirt")
    audience = t.get("audience", "dog moms and dog dads")
    desc = (
        f"{p.get('blurb', '')} "
        f"A soft, made-to-order tee for {audience}. "
        f"Great gift idea: {kw}. "
        f"Shop the Underdog Goods pack of original dog tees and join the waitlist."
    )
    return {"title": title, "description": desc[:500], "link": page_url(p)}


# ---------------------------------------------------------------------------
# Zernio client
# ---------------------------------------------------------------------------
def zernio(method, path, body=None):
    if not API_KEY:
        sys.exit("ZERNIO_API_KEY not set (source the project .env first)")
    url = ZERNIO_BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {API_KEY}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:500]
        sys.exit(f"Zernio {method} {path} -> HTTP {e.code}: {detail}")


def build_payload(platform, product, mode, scheduled_for):
    """One post, one platform, with platform-fitted content + platformSpecificData."""
    account_id = ACCOUNTS[platform]

    if platform == "tiktok":
        # TikTok is carousel/video-first: a single static photo barely reaches.
        # Post a branded multi-image photo carousel (hook -> tee -> design -> cta).
        media = [{"type": "image", "url": u} for u in carousel_frames(product)]
        # photo slideshow: caption == title (TikTok caps it at 90 chars)
        content = tiktok_photo_title(product)
        psd = {"privacy_level": "PUBLIC_TO_EVERYONE", "content_preview_confirmed": True}
    elif platform == "pinterest":
        # Pinterest pins are 1 image by design (no carousels) — a single strong pin.
        media = [{"type": "image", "url": mockup_url(product)}]
        pin = pinterest_pin(product)
        content = pin["description"]
        if not PINTEREST_BOARD:
            sys.exit("ZERNIO_PINTEREST_BOARD not set — Pinterest pins require a board id")
        psd = {"title": pin["title"], "boardId": PINTEREST_BOARD, "link": pin["link"]}
    else:
        sys.exit(f"unsupported platform: {platform}")

    payload = {
        "content": content,
        "profileId": PROFILE_ID,
        "mediaItems": media,
        "platforms": [{"platform": platform, "accountId": account_id, "platformSpecificData": psd}],
    }
    if mode == "now":
        payload["publishNow"] = True
    elif mode == "schedule":
        if not scheduled_for:
            sys.exit("--mode schedule requires --at <ISO8601>")
        payload["scheduledFor"] = scheduled_for
        payload["timezone"] = os.environ.get("TZ_NAME", "America/New_York")
    # mode == draft -> omit publishNow + scheduledFor
    return payload


def preview(platform, product):
    print(f"\n================= {platform.upper()}  ·  {product['name']} =================")
    if platform == "tiktok":
        print(tiktok_caption(product))
    else:
        pin = pinterest_pin(product)
        print(f"TITLE ({len(pin['title'])}/100): {pin['title']}")
        print(f"LINK : {pin['link']}")
        print(f"DESC ({len(pin['description'])}/500):\n{pin['description']}")
    print(f"IMAGE: {mockup_url(product)}")


def main():
    ap = argparse.ArgumentParser(description="Underdog Goods social marketing engine")
    ap.add_argument("--product", help="product slug")
    ap.add_argument("--all", action="store_true", help="run every product")
    ap.add_argument("--platforms", default="tiktok,pinterest", help="comma list: tiktok,pinterest")
    ap.add_argument("--mode", default="draft", choices=["draft", "schedule", "now"])
    ap.add_argument("--at", help="ISO8601 time for --mode schedule")
    ap.add_argument("--preview", action="store_true", help="print copy only, do not post")
    args = ap.parse_args()

    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    products = load_products() if args.all else [get_product(args.product)] if args.product else None
    if products is None:
        sys.exit("specify --product <slug> or --all")

    created = []
    for product in products:
        for platform in platforms:
            if args.preview:
                preview(platform, product)
                continue
            payload = build_payload(platform, product, args.mode, args.at)
            resp = zernio("POST", "/posts", payload)
            post = resp.get("post", resp)
            pid = post.get("_id") or post.get("id") or "?"
            status = post.get("status") or args.mode
            ledger_append(pid, product["slug"], platform, args.mode)
            created.append((platform, product["slug"], pid, status))
            print(f"  [{platform:9}] {product['slug']:26} -> post {pid}  ({status})")

    if created:
        print(f"\n{len(created)} post(s) created. Review them at https://zernio.com/dashboard/posts")


if __name__ == "__main__":
    main()
