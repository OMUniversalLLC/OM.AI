# OM AI deployment status

This repository contains source code and an illustrative browser preview. Importing it into GitHub **does not** deploy a live surveillance application or connect any private vendor or API accounts.

## Status

- GitHub code import: uploaded through a review branch.
- Local camera/NVR integration: requires on-site configuration and a camera-by-camera test.
- Google Sheets / Apps Script: requires a private Sheet, owner deployment and per-user access setup.
- Store PC / Wi-Fi agent: requires approved local installation and health checks.
- GasBuddy, AAA, MostEdge: provider-approved reports, exports or APIs must be configured; no scraping credentials are present.
- Gemini / OpenAI: optional provider API credentials stored privately, not in this repository.
- Screenshot and forecast preview: deliberately fictional data; not live.

## Before production

1. Review `docs/SECURITY.md` and make the repository private if it will contain store-specific security configurations.
2. Verify NVR continued recording and current storage health.
3. Verify signed local event upload without exposing RTSP or device admin ports.
4. Configure role-specific access, audit logs, and data retention.
5. Test all collectors and alerts against actual source evidence before enabling business decisions.
