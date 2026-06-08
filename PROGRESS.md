# Autonomous Build Progress — Cloud New-Design Pipeline

Started 2026-06-08. Plan: Printify/docs/superpowers/plans/2026-06-08-autonomous-design-pipeline.md

## Status
- [x] Phase 0: credentials + assets — ANTHROPIC + RECRAFT secrets set; blank-tee vendored; fonts via apt. DEPLOY KEY = user action (classifier-blocked).
- [x] Phase 1: font resolver (growth/fonts.py) + build_carousels wired — tests pass.
- [x] Phase 2: llm.py + brief_author.py + critic.py — validated locally with real Claude calls.
- [x] Phase 3: design_pipeline.py — validated end-to-end with real Recraft (UA header fixes Cloudflare 1010).
- [x] Phase 4: themes.json refactor + deploy.py + cycle.py auto branch + daily-cap stagger.
- [x] Phase 5: cloud wiring (run.sh clones walnut in auto; workflow installs Pillow+fonts, adds secrets).
- [~] Phase 6: verify + go-live — creative core proven locally (brief->render->critic->storefront->carousel,
      all real). REMAINING: WALNUT_DEPLOY_KEY (user), then one watched cycle, then flip GROWTH_MODE=auto.
- [ ] Phase 7: close-out (Pandora ingest).

## Validated locally (real APIs)
- brief_author -> "dog-parent-tax-tee" (complete brief, all keys, 44-char hook)
- design_pipeline.render -> Recraft art -> transparent -> tee composite (good quality)
- critic.review -> score 78, pass=true, thoughtful rationale
- build_carousels -> 4 frames + manifest, hook pulled from themes.json, fonts OK

## Untested (blocked on WALNUT_DEPLOY_KEY)
- deploy.push_walnut (cross-repo push), deploy.wait_for_url (Vercel), marketing_engine schedule of a new design.

## Handoff: ONE user action needed
Create the walnut write deploy key + secret (classifier won't let the agent do it). See SETUP.md.
After that: trigger one auto run, watch it, then set workflow GROWTH_MODE=auto.
