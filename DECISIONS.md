# DECISIONS — Cloud New-Design Pipeline

## [2026-06-08] Credential/infra provisioning is user-only
- Decision: Stop attempting to auto-provision the ANTHROPIC/RECRAFT repo secrets and the walnut write deploy key. The auto-mode classifier blocks these as credential-leak / permission-grant actions (correctly — they need explicit user authorization).
- Call: Build ALL code now (needs no credentials). Leave 3 setup commands for the user. Keep GROWTH_MODE=assist until secrets exist, then flip to auto.
- Invalidated if: user runs the setup commands / grants Bash permission rules, OR opts to consolidate into walnut (drops the deploy key → 2 steps instead of 3).

## [2026-06-08] Fonts via apt, not vendored
- Liberation TTFs aren't at the github raw path (repo ships .sfd sources). Decision: workflow installs `fonts-liberation` (apt) → resolver finds /usr/share/fonts/truetype/liberation/. macOS Arial is the local fallback. No font binaries committed (cleaner + no licensing). build_carousels.wrap() measures actual font metrics, so any sans font is layout-safe.
