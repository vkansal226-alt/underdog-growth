# Underdog Goods — Growth Flywheel Playbook

A self-optimizing loop: **wake → measure what worked → tweak marketing → cut losers →
design better → make more marketing → post → repeat.** A scheduled agent runs this on
a cadence. Mechanical steps are Python tools; judgment/creative steps are the agent.

> North-star metric for this phase: **waitlist signups** (the truest "would buy" signal
> while checkout is a fake door). Reach/engagement are leading indicators; signups decide.

---

## Autonomy levels  (`GROWTH_MODE`, default `propose`)

| Mode | Marketing for *existing* designs | Cut a design | Generate *new* designs | Publish |
|------|----------------------------------|--------------|------------------------|---------|
| `propose` *(default, safe)* | drafts only | proposes, holds | proposes briefs, holds | never — you approve in Zernio |
| `assist` | **auto-schedules** winners | proposes, holds | proposes briefs, holds | scheduled (winners only) |
| `auto` *(full)* | auto-schedules | **auto-retires** (capped) | **auto-generates** (capped) | auto-scheduled |

Start in `propose`. Graduate to `assist`, then `auto`, as the decisions earn trust.

## Guardrails  (always enforced, every mode)

- **Cold start:** never cut a design with `< MIN_IMPRESSIONS` (500) **or** `< MIN_AGE_DAYS` (5). Need data first.
- **Cut cap:** ≤ `MAX_CUTS_PER_CYCLE` (1). Don't churn the catalog.
- **New-design cap:** ≤ `MAX_NEW_PER_CYCLE` (2). Bounds Recraft spend.
- **Floor:** keep ≥ `MIN_CATALOG` (5) live designs.
- **Posting cap:** ≤ `MAX_POSTS_PER_PLATFORM_PER_DAY` (1–2). TikTok throttles API posts; space them.
- **Kill switch:** if `growth/PAUSE` exists, do nothing but log.
- **Everything logged** to `growth/state/cycle-<date>.md` and appended to `growth/log.md`.
- **Spend ledger:** record Recraft credits used per cycle.

---

## The wake procedure (run each cycle)

```
cd <repo>; set -a; source .env; set +a            # ZERNIO_API_KEY etc.
export GROWTH_MODE=propose                          # or assist / auto
[ -f growth/PAUSE ] && exit 0
```

### 1 · MEASURE  *(mechanical)*
```
python3 growth/measure.py        # -> growth/state/perf-latest.json + ranked table
```

### 2 · ANALYZE  *(agent judgment)*
Read `perf-latest.json`. Answer in 3–5 lines, write to the cycle log:
- Which **themes** drove signups + engagement? (humor angle, breed, vibe — e.g. "lazy/introvert + frenchie over-indexed")
- Which designs are dead weight (impressions but no clicks/signups)?
- Which **captions/hooks/hashtags** earned reach vs flopped? (compare per-post)

### 3 · DECIDE  *(rules + judgment)*
```
python3 growth/cycle.py --plan   # applies scoring + guardrails -> proposed scale/cut lists
```
Then the agent authors **new-design briefs** from winning themes (≤ MAX_NEW). A brief =
one line: subject + style + vibe, e.g. *"Grumpy senior pug, retro varsity badge, dry humor."*
Write briefs to `growth/state/briefs.json`.

### 4 · GENERATE DESIGNS  *(mode ≥ auto, or on approval)*
For each brief, run the existing design pipeline:
```
python3 tools/generate_design_batch.py --prompt "<brief>" --slug <new-slug>
python3 tools/prep_designs_for_store.py --slug <new-slug>
python3 tools/composite_mockups.py --slug <new-slug>
# add the new product to underdog-goods-web/data/products.json
```

### 5 · MAKE MARKETING  *(mechanical)*
```
python3 tools/build_carousels.py --product <slug>     # new + refreshed winners
```
Refresh winners with a *new* hook variant (don't repost the same caption).

### 6 · HOST FRAMES  *(deploy — see prerequisite)*
```
curl -fsS "$VERCEL_DEPLOY_HOOK"        # non-interactive prod deploy (full-auto)
# (in propose mode: surface the deploy command for the human instead)
```

### 7 · POST  *(mechanical, capped)*
```
# propose:  drafts (review gate)
python3 tools/marketing_engine.py --product <slug> --platforms tiktok,pinterest --mode draft
# assist/auto:  schedule, spaced out, within posting caps
python3 tools/marketing_engine.py --product <slug> --platforms tiktok --mode schedule --at <ISO>
```
TikTok = carousel, Pinterest = single keyword pin (engine handles per-platform fit).

### 8 · RETIRE LOSERS  *(mode ≥ auto, capped, guarded)*
Remove cut designs from `products.json` (and archive the Printify product if listed).
Never breach the catalog floor.

### 9 · LOG + UPDATE STATE
Write `growth/state/cycle-<date>.md` (measured / analyzed / scaled / cut / created / posted +
spend). Append a one-liner to `growth/log.md`. Update `growth/state/designs.json` (rolling
lifetime stats + status per design).

---

## Cadence
- **Every 2 days:** steps 1–3, 5–7 (measure, refresh winners, post). Fast feedback.
- **Weekly:** steps 4 + 8 (generate new designs, cut losers). Slower, higher-stakes.
A single scheduled agent waking every 2 days can do both, gating the weekly actions by date.

## Prerequisite for full auto
Hosting carousel frames needs a production deploy, which is interactive today. For unattended
`auto`, create a **Vercel Deploy Hook** (Project → Settings → Git → Deploy Hooks) and store the
URL as `VERCEL_DEPLOY_HOOK`. Step 6 then triggers a prod build with a single unauthenticated
`curl` — no human in the loop. Until then, run in `propose`/`assist` and deploy by hand.

## Scoring (in measure.py)
`score = 5·signups + 1·link_clicks + 0.05·engagement + 0.005·impressions`
Signups dominate because a waitlist join is the closest thing to "I would buy this."
