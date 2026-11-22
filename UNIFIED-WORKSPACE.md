# OM AI — Unified source workspace

This is the canonical GitHub repository for OM AI source code.

## Applications
- `apps/operations-dashboard` — imported React operations reporting dashboard. Its independent Google sign-in integration and hardcoded Pages path are legacy code, **not** Supabase-integrated.
- `apps-script` — existing private OM AI Google Apps Script prototype.
- `surveillance`, `edge-agent` — proposed NVR/edge analytics integration.
- `network-agent`, `pc-agent` — store Windows network and computer-health agents.
- `preview` — illustrative user interface (not live operational readings).

### Import status
The React dashboard source was copied from `OMUniversalLLC/om-universal-operations-dashboard` into `apps/operations-dashboard`. The original repo has **not** been changed. We intentionally excluded the published sales snapshot, prebuilt assets, old workflows and redundant README to avoid redistributing operational data or accidentally enabling scheduled login automations. The imported app has an **empty, safe placeholder** instead.

This import is a source-code consolidation, **not** a deployed single-sign-on or integrated data pipeline. See `docs/UNIFIED-SECURITY-AND-DEPLOYMENT.md` before enabling live use.

## Run imported dashboard (developer only)
```bash
cd apps/operations-dashboard
pnpm install
pnpm run dev:pages
```
For this unified repo, the legacy GitHub Pages base path and auth endpoints must be migrated before deployment.

## Data and secrets
Never put passwords, authentication tokens, private camera addresses/footage, real store reports or database service-role keys in GitHub. Supabase will authenticate **OM AI human users only**; separate backend/edge service vaults store external credentials. Do not store external account passwords in Supabase Auth.
