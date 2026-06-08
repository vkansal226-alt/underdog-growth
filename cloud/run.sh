#!/bin/bash
# Underdog Goods growth loop — cloud runner.
# propose/assist: measure + (assist) schedule winners. auto: also author, vet, and
# publish brand-new designs to the storefront (walnut) and post them.
cd "$(dirname "$0")/.." || exit 1
export PYTHONPATH="$PWD"
export UNDERDOG_THEMES="$PWD/growth/state/themes.json"
export SUPABASE_URL="${SUPABASE_URL:-https://ctxihylqvpajgkctxrsg.supabase.co}"
export SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY:-sb_publishable_cY-t-W6GbCkIK1EK3tvarg_KKBJtlEF}"
export SITE_BASE="${SITE_BASE:-https://underdog-goods.vercel.app}"
export ZERNIO_PROFILE_ID="${ZERNIO_PROFILE_ID:-6a1f7e7f5764bf632edb335e}"
export ZERNIO_TIKTOK_ACCOUNT="${ZERNIO_TIKTOK_ACCOUNT:-6a20c2af2b2567671abcb513}"
export ZERNIO_PINTEREST_ACCOUNT="${ZERNIO_PINTEREST_ACCOUNT:-6a20c3322b2567671abcbb77}"
export ZERNIO_PINTEREST_BOARD="${ZERNIO_PINTEREST_BOARD:-1083397322800608158}"
export GROWTH_MODE="${GROWTH_MODE:-propose}"

[ -f growth/PAUSE ] && { echo PAUSED; exit 0; }

if [ "$GROWTH_MODE" = "auto" ]; then
  # auto mode needs the storefront checked out (write deploy key) so new designs
  # commit + deploy there. Fall back to measure-only if the key is missing.
  if [ -n "$WALNUT_DEPLOY_KEY" ]; then
    mkdir -p ~/.ssh && printf '%s\n' "$WALNUT_DEPLOY_KEY" > ~/.ssh/walnut && chmod 600 ~/.ssh/walnut
    export GIT_SSH_COMMAND="ssh -i ~/.ssh/walnut -o StrictHostKeyChecking=no"
    rm -rf /tmp/walnut
    if git clone -q git@github.com:vkansal226-alt/walnut.git /tmp/walnut; then
      export UNDERDOG_WEB=/tmp/walnut
      export UNDERDOG_PRODUCTS=/tmp/walnut/data/products.json
      export UNDERDOG_MANIFEST=/tmp/walnut/public/social/manifest.json
    else
      echo "::warning::walnut clone failed — auto new-design step will be skipped"
    fi
  else
    echo "::warning::WALNUT_DEPLOY_KEY not set — auto new-design step will be skipped"
  fi
fi

# measure-only fallback paths (propose/assist, or auto without a walnut checkout)
export UNDERDOG_PRODUCTS="${UNDERDOG_PRODUCTS:-$PWD/data/products.json}"
export UNDERDOG_MANIFEST="${UNDERDOG_MANIFEST:-$PWD/data/manifest.json}"

python3 growth/cycle.py --plan
python3 growth/cycle.py --execute
