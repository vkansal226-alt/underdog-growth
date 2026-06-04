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
    subprocess.run([sys.executable, os.path.join(HERE, "measure.py")], check=False)
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


def execute(dry):
    if not os.path.exists(PLAN):
        plan()
    p = json.load(open(PLAN))
    post_mode = "draft" if MODE == "propose" else "schedule"
    print(f"\nEXECUTE  mode={MODE}  -> marketing as '{post_mode}'  (dry_run={dry})")

    # 1) refresh marketing for SCALE designs (known winners) — safe in every mode.
    # Frames already exist + are hosted, so refresh = a fresh post (no PIL/deploy needed);
    # this keeps the cycle runnable in a cloud env with no image toolchain.
    for slug in p["scale"]:
        cmd = [sys.executable, ENGINE, "--product", slug, "--platforms", "tiktok,pinterest", "--mode", post_mode]
        if post_mode == "schedule":
            when = (datetime.datetime.now() + datetime.timedelta(days=1)).replace(microsecond=0).isoformat()
            cmd += ["--at", when]
        sh(cmd, dry)

    # 2) NEW designs — agent-authored briefs, only in auto, capped (surfaced, not silently run)
    briefs = json.load(open(BRIEFS)) if os.path.exists(BRIEFS) else []
    if briefs:
        print(f"  NEW briefs found ({len(briefs)}); budget={p['new_design_budget']}.")
        for b in briefs[: p["new_design_budget"]]:
            print(f"    brief: {b}")
            print("      -> run the Recraft pipeline (generate_design_batch -> prep -> composite),")
            print("         add to products.json, then build_carousels + engine. (guarded: needs --confirm)")
    else:
        print("  NEW: no briefs.json yet — agent supplies briefs from the perf report.")

    # 3) CUTS — destructive; surfaced for confirmation, never auto-deleted here
    if p["cut"]:
        print(f"  CUT proposed: {p['cut']}  -> remove from products.json + archive Printify listing (needs --confirm).")

    if MODE != "propose" and post_mode == "schedule":
        print("  reminder: full-auto posting needs hosted frames — set VERCEL_DEPLOY_HOOK (see PLAYBOOK).")


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
