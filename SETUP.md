# Go-Live Setup — Autonomous New-Design Pipeline

The pipeline is built and the creative core is validated. Two secrets are already
set (`ANTHROPIC_API_KEY`, `RECRAFT_API_KEY`). **One step remains that only you can do**:
the agent's security sandbox blocks it from creating a write deploy key on another repo.

## Step 1 — give the loop write access to the storefront (walnut)

Run this once (locally, where `gh` is logged in as you). It makes a key, grants it
write access to `walnut`, stores the private half as a secret on `underdog-growth`,
and cleans up:

```bash
ssh-keygen -t ed25519 -N "" -C growth-bot@underdog -f /tmp/wk \
 && gh repo deploy-key add /tmp/wk.pub -R vkansal226-alt/walnut --title growth-bot-write --allow-write \
 && gh secret set WALNUT_DEPLOY_KEY -R vkansal226-alt/underdog-growth < /tmp/wk \
 && rm -f /tmp/wk /tmp/wk.pub \
 && echo "WALNUT_DEPLOY_KEY installed"
```

## Step 2 — one watched test cycle

```bash
gh workflow run growth-loop -R vkansal226-alt/underdog-growth -f # (or use the Run workflow button)
```

It still runs in `assist` while you verify. To actually exercise auto once, temporarily
set `GROWTH_MODE: auto` in `.github/workflows/growth.yml`, trigger a run, and confirm:
a new product appears in `walnut/data/products.json`, frames go live at
`https://underdog-goods.vercel.app/social/<slug>/01-hook.png`, the critic verdict is
logged, and exactly one Zernio post is scheduled.

## Step 3 — leave it on auto

Set `GROWTH_MODE: auto` in `.github/workflows/growth.yml`, commit + push. The loop then
runs every 2 days: measure -> author new design(s) -> render -> critic gate -> publish
survivors -> schedule posts, plus scaling proven winners. Fully hands-off.

## Controls
- **Kill switch:** create an empty file `growth/PAUSE` (commit it) to halt all cycles.
- **Threshold / volume:** `CRITIC_THRESHOLD` (default 70), `MAX_NEW_PER_CYCLE` (default 2).
- Cuts are never automatic — always surfaced for confirmation.
