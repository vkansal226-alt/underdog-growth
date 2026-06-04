#!/bin/bash
# Underdog Goods growth loop — cloud runner (PROPOSE mode). ZERNIO_API_KEY via env.
cd "$(dirname "$0")/.." || exit 1
export UNDERDOG_PRODUCTS="$PWD/data/products.json"
export UNDERDOG_MANIFEST="$PWD/data/manifest.json"
export SUPABASE_URL="${SUPABASE_URL:-https://ctxihylqvpajgkctxrsg.supabase.co}"
export SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY:-sb_publishable_cY-t-W6GbCkIK1EK3tvarg_KKBJtlEF}"
export SITE_BASE="${SITE_BASE:-https://underdog-goods.vercel.app}"
export ZERNIO_PROFILE_ID="${ZERNIO_PROFILE_ID:-6a1f7e7f5764bf632edb335e}"
export ZERNIO_TIKTOK_ACCOUNT="${ZERNIO_TIKTOK_ACCOUNT:-6a20c2af2b2567671abcb513}"
export ZERNIO_PINTEREST_ACCOUNT="${ZERNIO_PINTEREST_ACCOUNT:-6a20c3322b2567671abcbb77}"
export ZERNIO_PINTEREST_BOARD="${ZERNIO_PINTEREST_BOARD:-1083397322800608158}"
export GROWTH_MODE="${GROWTH_MODE:-propose}"
[ -f growth/PAUSE ] && { echo PAUSED; exit 0; }
python3 growth/cycle.py --plan
python3 growth/cycle.py --execute
