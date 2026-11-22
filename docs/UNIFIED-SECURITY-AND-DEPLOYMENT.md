# OM AI — Credential and deployment plan

## Repository consolidation
This repository contains two **separate** applications while integration is in progress:
- `apps/operations-dashboard/`: imported React operations dashboard source.
- `apps-script/`, `surveillance/`, `network-agent/`, `pc-agent/`: OM AI monitoring components.

The original operations-dashboard repository and its current deployment are unchanged. Its published real-data snapshot, compiled assets, and active GitHub Actions workflows were deliberately **not imported**. A no-data JSON placeholder is used instead. The imported app's old GitHub Pages base path and Google login are historical code; do not deploy as a unified production application until routes and security are migrated.

## What GitHub Secrets and Variables are for
**Actions secrets** are suitable for credentials of CI/build/deployment jobs. In GitHub: Settings → Secrets and variables → Actions → New repository secret. Use environment-scoped secrets when available and protect production environments. Never echo secrets, put them in output artifacts, or allow untrusted PRs to access them. **Actions variables** are for non-sensitive settings (e.g. deployment target name). Neither is a general runtime password manager for browsers, local camera agents, or a website frontend.

## OM AI sign-in and third-party credentials
- **Supabase Auth** is intended **only for human OM AI users**. Public URL and anon/publishable key may be used in a browser; service-role / secret keys are server-side only. Supabase auth is **not yet implemented** for this legacy Google Apps Script app.
- Keep third-party service logins (private operations portals, permitted data feeds) inside a managed backend secret vault, or authorized local machine credential store. Do not save passwords in Google Sheets, GitHub, or Supabase Auth profiles.
- Keep camera/NVR/RTSP credentials on the store's protected edge computer. Send the website signed aggregate telemetry over authenticated HTTPS; do not publicly expose RTSP/NVR, RDP, or private LAN services.
- Do not automate websites against their terms, and do not assume they offer supported APIs. An authenticated export or licensed integration is preferred.
- Securely store backend credentials in production host secret manager (for example Supabase Vault for appropriate server-side workflows, or hosting-provider encrypted secrets), with access scoped to services and audited.
- Require server-side store/role authorization and MFA for administrators; use row-level security if using Supabase Postgres.
- Do not forward external provider passwords to OpenAI/Gemini models.

## Checklist before production
1. Complete separate data/API authentication design; do **not** treat a public static app or Google Sheet as a secret-protected backend.
2. Set up Supabase Auth for owner/admin/manager/staff only after establishing a backend that verifies signed tokens and enforces store access.
3. Move credential configuration into secrets manager, add service healthchecks and rotation guidance.
4. Verify CI variables are non-sensitive and secrets are restricted to trusted workflows.
5. Review any previously public GitHub commit history before using the repository for private operations.
6. Configure a new deployment route and test with no private data in client bundles.
7. Test every camera/PC connector on-site, with passwords only entered through protected local interfaces.
