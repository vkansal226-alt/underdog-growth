#!/usr/bin/env python3
"""
Growth loop · ORCHESTRATOR.

Ties the flywheel together with guardrails. See growth/PLAYBOOK.md for the full
loop; this is the deterministic harness. Judgment/creative steps (theme analysis,
new-design briefs, fresh hooks) are the agent's job and are surfaced, not faked.

  cycle.py --plan              measure + classify (scale/hold/cut) + write plan, print
  cycle.py --execute           act on the plan in $GROWTH_MODE (draft|schedule winners)
  cycle.py --execute --dry-run print the actions without running them

Modes (env GROWTH_MODE): propose (default) | assist | auto
Guardrails (env overridable): MIN_IMPRESSIONS, MIN_AGE_DAYS, MAX_CUTS_PER_CYCLE,
  MAX_NEW_PER_CYCLE, MIN_CATALOG, MAX_POSTS_PER_PLATFORM_PER_DAY
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATE = os.path.join(HERE, "state")
PERF = os.path.join(STATE, "perf-latest.json")
PLAN = os.path.join(STATE, "plan-latest.json")
LEDGER = os.path.join(STATE, "posts.json")
BRIEFS = os.path.join(STATE, "briefs.json")
LOG = os.path.join(HERE, "log.md")

MODE = os.environ.get("GROWTH_MODE", "propose")
CFG = {
    "MIN_IMPRESSIONS": int(os.environ.get("MIN_IMPRESSIONS", 500)),
    "MIN_AGE_DAYS": int(os.environ.get("MIN_AGE_DAYS", 5)),
    "MAX_CUTS_PER_CYCLE": int(os.environ.get("MAX_CUTS_PER_CYCLE", 1)),
    "MAX_NEW_PER_CYCLE": int(os.environ.get("MAX_NEW_PER_CYCLE", 2)),
    "MIN_CATALOG": int(os.environ.get("MIN_CATALOG", 5)),
    "MAX_POSTS_PER_PLATFORM_PER_DAY": int(os.environ.get("MAX_POSTS_PER_PLATFORM_PER_DAY", 1)),
}
ENGINE = os.path.join(ROOT, "tools", "marketing_engine.py")
CAROUSEL = os.path.join(ROOT, "tools", "build_carousels.py")


def sh(cmd, dry):
    print("    $ " + " ".join(cmd))
    if dry:
        return
    subprocess.run(cmd, check=False)


def first_seen(ledger, slug):
    """Earliest ledger 'created' for a design, as a date (cold-start age guard)."""
    dates = [v.get("created") for v in ledger.values() if v.get("slug") == slug and v.get("created")]
    if not dates:
        return None
    try:
        return min(datetime.datetime.fromisoformat(d) for d in dates)
    except Exception:
        return None


def plan():
    if os.path.exists(os.path.join(HERE, "PAUSE")):
        print("PAUSE file present — halting (logging only).")
        sys.exit(0)
    # fresh measurement
    r = subprocess.run([sys.executable, os.path.join(HERE, "measure.py")], check=False)
    if r.returncode != 0:
        print(f"  ::warning:: measure.py exited {r.returncode} — planning on STALE perf if present")
    if not os.path.exists(PERF):
        sys.exit("no perf report; run measure first")
    perf = json.load(open(PERF))
    ledger = json.load(open(LEDGER)) if os.path.exists(LEDGER) else {}
    designs = perf["designs"]
    now = datetime.datetime.now()

    scale, hold, cut_eligible = [], [], []
    for slug, a in designs.items():
        seen = first_seen(ledger, slug)
        age_days = (now - seen).days if seen else 0
        has_signal = a["score"] > 0
        old_enough = age_days >= CFG["MIN_AGE_DAYS"]
        seen_enough = a["impressions"] >= CFG["MIN_IMPRESSIONS"]
        if has_signal:
            scale.append(slug)
        elif old_enough and seen_enough and a["signups"] == 0 and a["clicks"] == 0:
            cut_eligible.append(slug)  # had its shot, no demand
        else:
            hold.append(slug)  # not enough data yet — guarded

    # enforce caps + catalog floor
    live = len(designs)
    cuts = cut_eligible[: CFG["MAX_CUTS_PER_CYCLE"]]
    if live - len(cuts) < CFG["MIN_CATALOG"]:
        cuts = cuts[: max(0, live - CFG["MIN_CATALOG"])]
    scale = scale[:3]

    out = {
        "generated": now.isoformat(timespec="seconds"),
        "mode": MODE, "config": CFG,
        "scale": scale, "hold": hold, "cut": cuts,
        "new_design_budget": CFG["MAX_NEW_PER_CYCLE"],
    }
    os.makedirs(STATE, exist_ok=True)
    json.dump(out, open(PLAN, "w"), indent=2)

    print(f"\nPLAN  mode={MODE}")
    print(f"  SCALE ({len(scale)}): {scale or '—'}")
    print(f"  HOLD  ({len(hold)}): {hold if len(hold) <= 8 else hold[:8] + ['…']}")
    print(f"  CUT   ({len(cuts)}): {cuts or '—'}   [eligible before caps: {cut_eligible or '—'}]")
    if not scale and not cuts:
        print("  -> no signal yet. Holding the catalog; post fresh marketing to gather data.")
    print("  AGENT TODO (judgment): write new-design briefs from winning themes to growth/state/briefs.json")
    return out


SITE = os.environ.get("SITE_BASE", "https://underdog-goods.vercel.app").rstrip("/")
WEB = os.environ.get("UNDERDOG_WEB", "")
THEMES_PATH = os.environ.get("UNDERDOG_THEMES", os.path.join(STATE, "themes.json"))


def _slot(counter):
    """21:00 UTC, staggered one per call starting tomorrow — honors 1 post/platform/day."""
    d = datetime.datetime.now(datetime.timezone.utc).date() + datetime.timedelta(days=1 + counter)
    return datetime.datetime.combine(d, datetime.time(hour=21)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _schedule_base():
    """Day offset so new posts land AFTER anything already scheduled in Zernio —
    avoids stacking a fresh design on top of the existing queue."""
    key = os.environ.get("ZERNIO_API_KEY")
    if not key:
        return 0
    try:
        import urllib.request
        req = urllib.request.Request("https://zernio.com/api/v1/posts?limit=50")
        req.add_header("Authorization", f"Bearer {key}")
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())
        posts = d.get("posts", d if isinstance(d, list) else d.get("data", []))
        today = datetime.datetime.now(datetime.timezone.utc).date()
        latest = today
        for p in posts:
            if p.get("status") == "scheduled" and p.get("scheduledFor"):
                try:
                    dt = datetime.datetime.fromisoformat(p["scheduledFor"].replace("Z", "+00:00")).date()
                    latest = max(latest, dt)
                except Exception:
                    pass
        return max(0, (latest - today).days)  # _slot adds tomorrow, so first lands at latest+1
    except Exception:
        return 0


def _load_products(web):
    pth = os.path.join(web, "data", "products.json")
    d = json.load(open(pth))
    return (d if isinstance(d, list) else d.get("products", [])), pth


def _slug_exists(web, slug):
    items, _ = _load_products(web)
    return any(p.get("slug") == slug for p in items)


def _add_product(web, brief, render):
    pth = os.path.join(web, "data", "products.json")
    data = json.load(open(pth))                 # preserve the {brand, products} wrapper
    entry = {
        "slug": brief["slug"], "name": brief["name"],
        "price_usd": brief.get("price_usd", 19.99),
        "headline": brief.get("headline", ""), "story": brief.get("story", ""),
        "design": render["design"], "mockup": render["mockup"],
        "colors": brief.get("colors", []), "checkout_url": "",
        "blurb": brief.get("blurb", ""),
    }
    if isinstance(data, list):
        data.append(entry)
    else:
        data.setdefault("products", []).append(entry)
    json.dump(data, open(pth, "w"), indent=2)


def _add_theme(brief):
    os.makedirs(os.path.dirname(THEMES_PATH), exist_ok=True)
    data = json.load(open(THEMES_PATH)) if os.path.exists(THEMES_PATH) else {}
    data[brief["slug"]] = brief.get("social", {})
    json.dump(data, open(THEMES_PATH, "w"), indent=2)


def _schedule(slug, counter, dry):
    sh([sys.executable, ENGINE, "--product", slug, "--platforms", "tiktok,pinterest",
        "--mode", "schedule", "--at", _slot(counter)], dry)


def _auto_new_designs(p, slot, dry):
    """auto mode: author briefs -> render -> critic gate -> publish survivors to walnut."""
    from growth import brief_author, critic, design_pipeline, deploy
    if not WEB:
        print("  AUTO: UNDERDOG_WEB unset (no storefront checkout) — skipping new designs.")
        return slot
    budget = p["new_design_budget"]
    if dry:
        print(f"  AUTO (dry): would author up to {budget} brief(s), render+critic, publish survivors.")
        return slot
    briefs = brief_author.author(budget)
    print(f"  AUTO: authored {len(briefs)} brief(s).")
    accepted = []
    for b in briefs:
        slug = b.get("slug")
        try:
            if not slug or _slug_exists(WEB, slug):
                print(f"    skip {slug}: already exists or invalid")
                continue
            r = design_pipeline.render(slug, b["recraft_prompt"], WEB)
            v = critic.review(r["mockup_path"])
            print(f"    critic {slug}: score={v['score']} pass={v['pass']} — {v.get('reasons','')[:90]}")
            if not v["pass"]:
                for f in (r["mockup_path"], os.path.join(WEB, "public", r["design"].lstrip("/"))):
                    try:
                        os.remove(f)
                    except OSError:
                        pass
                continue
            _add_theme(b)                       # social copy (incl carousel hook) before frames
            _add_product(WEB, b, r)
            sh([sys.executable, CAROUSEL, "--product", slug], dry)
            accepted.append(slug)
        except Exception as e:                  # isolate failures — never block siblings
            print(f"    brief {slug} failed: {e}")
    if not accepted:
        print("  AUTO: no new designs passed the critic this cycle.")
        return slot
    ok, _ = deploy.deploy_vercel(WEB)
    if not ok:
        print("  AUTO: vercel deploy failed — designs built locally; will post next cycle.")
        return slot
    vault = os.environ.get("UNDERDOG_VAULT", "")
    rel = os.path.relpath(WEB, vault) if vault else WEB
    for slug in accepted:
        if deploy.wait_for_url(f"{SITE}/social/{slug}/01-hook.png", timeout=300):
            _schedule(slug, slot, dry)
            slot += 1
            deploy.persist_to_vault(vault, [
                os.path.join(rel, "data", "products.json"),
                os.path.join(rel, "public", "product-shots", f"{slug}.png"),
                os.path.join(rel, "public", "product-shots", f"{slug}-tee.png"),
                os.path.join(rel, "public", "social", slug),
            ], f"design-bot: new design {slug}")
        else:
            print(f"    {slug}: frame not live on Vercel yet; will post next cycle")
    return slot


def execute(dry):
    if not os.path.exists(PLAN):
        plan()
    p = json.load(open(PLAN))
    post_mode = "draft" if MODE == "propose" else "schedule"
    print(f"\nEXECUTE  mode={MODE}  -> marketing as '{post_mode}'  (dry_run={dry})")
    # global stagger counter: 1 post/platform/day, starting after the existing queue
    slot = _schedule_base() if post_mode == "schedule" else 0

    # 1) refresh marketing for SCALE designs (known winners) — safe in every mode.
    for slug in p["scale"]:
        if post_mode == "schedule":
            _schedule(slug, slot, dry)
            slot += 1
        else:
            sh([sys.executable, ENGINE, "--product", slug, "--platforms", "tiktok,pinterest", "--mode", "draft"], dry)

    # 2) NEW designs — auto mode authors + vets + publishes; assist/propose only surface.
    if MODE == "auto":
        slot = _auto_new_designs(p, slot, dry)
    else:
        n = len(json.load(open(BRIEFS))) if os.path.exists(BRIEFS) else 0
        print(f"  NEW: {n} brief(s) queued; switch GROWTH_MODE=auto to author + publish new designs.")

    # 3) CUTS — destructive; surfaced for confirmation, never auto-deleted here
    if p["cut"]:
        print(f"  CUT proposed: {p['cut']}  -> remove from products.json + archive listing (needs --confirm).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.plan or not args.execute:
        plan()
    if args.execute:
        execute(args.dry_run)


if __name__ == "__main__":
    main()
