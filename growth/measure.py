#!/usr/bin/env python3
"""
Growth loop · MEASURE phase.

Pulls real signal and produces a per-design performance report:
  - Zernio per-post analytics (impressions, engagement, link clicks) per platform,
    joined back to the design via growth/state/posts.json (the attribution ledger).
  - Supabase waitlist signups per product_slug (the demand signal we own end-to-end)
    via the underdog_metrics() RPC.

A per-design SCORE weights what matters for a demand test:
    score = 5*signups + 1.0*link_clicks + 0.05*engagement + 0.005*impressions
(signups dominate — a waitlist join is the truest "would buy" signal.)

Outputs:
  growth/state/perf-latest.json   machine-readable report (consumed by decide/cycle)
  prints a human summary

Env:
  ZERNIO_API_KEY            (from project .env)
  SUPABASE_URL / SUPABASE_ANON_KEY  (auto-read from underdog-goods-web/.env.local if unset)
"""
import datetime
import json
import os
import sys
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state")
LEDGER = os.path.join(STATE, "posts.json")
PRODUCTS = os.environ.get(
    "UNDERDOG_PRODUCTS",
    "/Users/Claude/Desktop/Pandora/projects/underdog-goods-web/data/products.json",
)
WEB_ENV = "/Users/Claude/Desktop/Pandora/projects/underdog-goods-web/.env.local"
ZERNIO = "https://zernio.com/api/v1"
PLATFORMS = ["tiktok", "pinterest"]

# scoring weights — signups dominate
W = {"signups": 5.0, "clicks": 1.0, "engagement": 0.05, "impressions": 0.005}


def _read_env_file(path, key):
    if not os.path.exists(path):
        return None
    for line in open(path):
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return None


ZKEY = os.environ.get("ZERNIO_API_KEY", "")
SUPA_URL = os.environ.get("SUPABASE_URL") or _read_env_file(WEB_ENV, "SUPABASE_URL")
SUPA_KEY = os.environ.get("SUPABASE_ANON_KEY") or _read_env_file(WEB_ENV, "SUPABASE_ANON_KEY")


def _get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  (GET {url[:60]}... -> {e.code})")
        return {}
    except Exception as e:
        print(f"  (GET failed: {e})")
        return {}


def _post(url, headers, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  (RPC failed: {e})")
        return []


def load_products():
    d = json.load(open(PRODUCTS))
    return d if isinstance(d, list) else d.get("products", d)


def load_ledger():
    return json.load(open(LEDGER)) if os.path.exists(LEDGER) else {}


def zernio_posts(platform):
    """Per-post analytics rows for a platform (list)."""
    today = datetime.date.today()
    frm = (today - datetime.timedelta(days=30)).isoformat()
    url = f"{ZERNIO}/analytics?platform={platform}&fromDate={frm}&toDate={today.isoformat()}"
    data = _get(url, {"Authorization": f"Bearer {ZKEY}"})
    return data.get("posts", []) if isinstance(data, dict) else []


def post_metrics(row):
    """Normalize a Zernio analytics post row into impressions/engagement/clicks."""
    m = row.get("metrics") or row.get("analytics") or row
    def g(*names):
        for n in names:
            if isinstance(m, dict) and m.get(n) is not None:
                return m.get(n) or 0
        return 0
    impressions = g("impressions", "views", "reach", "videoViews")
    likes = g("likes", "reactions")
    comments = g("comments")
    shares = g("shares", "reposts")
    saves = g("saves", "bookmarks")
    clicks = g("linkClicks", "clicks", "outboundClicks", "pinClicks")
    engagement = (likes or 0) + (comments or 0) + (shares or 0) + (saves or 0)
    return {"impressions": impressions or 0, "engagement": engagement, "clicks": clicks or 0}


def supabase_signups():
    """{slug: signup_count} from the underdog_metrics() RPC. Defensive about shape."""
    if not (SUPA_URL and SUPA_KEY):
        return {}
    rows = _post(
        f"{SUPA_URL}/rest/v1/rpc/underdog_metrics",
        {"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}", "Content-Type": "application/json"},
        {},
    )
    out = {}
    if isinstance(rows, list):
        for r in rows:
            if not isinstance(r, dict):
                continue
            slug = r.get("product_slug") or r.get("slug")
            n = r.get("signups") or r.get("count") or r.get("total") or 0
            if slug:
                out[slug] = out.get(slug, 0) + int(n)
    return out


def main():
    if not ZKEY:
        sys.exit("ZERNIO_API_KEY not set (source project .env)")
    ledger = load_ledger()
    products = {p["slug"]: p for p in load_products()}

    # seed per-design aggregates
    agg = {slug: {"name": p["name"], "platforms": {}, "impressions": 0,
                  "engagement": 0, "clicks": 0, "signups": 0, "posts": 0}
           for slug, p in products.items()}

    # join Zernio per-post analytics -> design via ledger (id match), else skip
    for platform in PLATFORMS:
        for row in zernio_posts(platform):
            pid = row.get("_id") or row.get("postId") or row.get("id")
            slug = (ledger.get(pid) or {}).get("slug") if pid else None
            if slug not in agg:
                continue
            m = post_metrics(row)
            a = agg[slug]
            a["impressions"] += m["impressions"]
            a["engagement"] += m["engagement"]
            a["clicks"] += m["clicks"]
            a["posts"] += 1
            a["platforms"][platform] = a["platforms"].get(platform, 0) + 1

    # signups
    for slug, n in supabase_signups().items():
        if slug in agg:
            agg[slug]["signups"] = n

    # score + rank
    for slug, a in agg.items():
        a["score"] = round(
            W["signups"] * a["signups"] + W["clicks"] * a["clicks"]
            + W["engagement"] * a["engagement"] + W["impressions"] * a["impressions"], 2)
    ranked = sorted(agg.items(), key=lambda kv: kv[1]["score"], reverse=True)

    report = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "totals": {
            "designs": len(agg),
            "impressions": sum(a["impressions"] for a in agg.values()),
            "signups": sum(a["signups"] for a in agg.values()),
            "live_posts_measured": sum(a["posts"] for a in agg.values()),
        },
        "designs": {slug: a for slug, a in ranked},
    }
    os.makedirs(STATE, exist_ok=True)
    json.dump(report, open(os.path.join(STATE, "perf-latest.json"), "w"), indent=2)

    t = report["totals"]
    print(f"MEASURE {report['generated']}")
    print(f"  designs={t['designs']}  posts_measured={t['live_posts_measured']}  "
          f"impressions={t['impressions']}  signups={t['signups']}")
    print("  rank  design                       score  imp   eng   clk  signup")
    for i, (slug, a) in enumerate(ranked, 1):
        print(f"  {i:>2}.  {slug:26} {a['score']:>6}  {a['impressions']:>4}  "
              f"{a['engagement']:>4}  {a['clicks']:>3}  {a['signups']:>4}")
    if t["live_posts_measured"] == 0:
        print("  note: no published posts yet — report is a baseline; cuts are guarded until data exists.")


if __name__ == "__main__":
    main()
