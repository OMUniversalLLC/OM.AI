# OM AI — Operations Monitoring & Artificial Intelligence

> **Unified repository:** The original React operations dashboard source has been imported under `apps/operations-dashboard/`. Read [UNIFIED-WORKSPACE.md](UNIFIED-WORKSPACE.md) and [security/deployment guidance](docs/UNIFIED-SECURITY-AND-DEPLOYMENT.md) before deploying. Supabase human-user authentication is planned, **not yet connected**. The imported dashboard retains legacy Google login code, and no live accounts or camera connections have been activated.


> **Deployment status:** source package and fictional preview only. The NVR, store Windows PC, Wi-Fi, POS, fuel sources, Gemini/OpenAI APIs, and Google Sheets are **not** connected by this GitHub commit. Follow `docs/SETUP.md` and verify all integrations before relying on readings.

> **Public repository safety:** All IP addresses in examples are documentation placeholders. Credentials, actual camera-stream URLs, device inventory exports, and customer/employee information must stay outside this repository.


## New: OM PC Intelligence + OM Orchestrator (Nov 19, 2026)

The private OM AI dashboard now includes **OM PC** (Windows health monitoring and safe optimization advice) and **OM Orchestrator** (actual task-run receipts, overdue/failure/evidence checks, manager audit reviews and optional Gemini/OpenAI task reasoning). A lightweight **Windows PC Companion** desktop app is included under `pc-agent/desktop_app.py`. The agent never stops programs or changes operating-system settings. Temperature / GPU values require a separately verified local sensor provider and show **Not measured** when unavailable. Approved source jobs may report actual success/failure, but no login to GasBuddy, AAA, MostEdge, ChatGPT, Gemini, POS, or NVR is established by this package.

Follow **`docs/PC-INTELLIGENCE-ORCHESTRATOR.md`** for installation, privacy, signed private ingestion and staged verification. New Apps Script files: `PcTaskMonitor.gs`, `ServiceJobs.gs`, `AiOps.gs`; new private Sheet tabs: `PcStatus`, `PcJobs`, `PcAlerts`, `JobReviews`, `ServiceJobs`. The existing live/public website has NOT been changed.

## Updated actual iLink NVR camera inventory (November 2026)

**IMPORTANT:** The user-supplied camera report supersedes the earlier hypothetical 14-camera layout. This edition now includes the 14 actual camera names, equipment profile and a test-first AI plan. Road and car-wash cameras have NOT been located. All camera analytics default to disabled and no live readings are fabricated. Read **`docs/NVR-ACTUAL-INVENTORY-AND-AI-PLAN.md`** before configuring an NVR, migration or AI detector. This code is not deployed.

# OM AI — Operations Monitoring & Artificial Intelligence

**A complete, editable private MVP for OM Universal LLC.** Built for Quick-C SUNOCO, Inverness Store, and Puff Republic / Vape Store. Source code is included; no live credentials, customer records or confidential Google Sheet data are in this ZIP.


### New: 14-camera OM Cameras + local event collector (Nov 2026)

The `surveillance/` folder adds a proposed 14-channel camera plan, optional Frigate/MQTT integration, local deduplicated vehicle/pump/store/wash event counts, explicit stream heartbeats, authorized POS/controller verification, signed HMAC aggregate export to the private Apps Script backend, observer tasks, and a responsive **OM Cameras** dashboard. **There is no live camera access until the existing DVR/RTSP feeds and hardware are configured.** Read `docs/SURVEILLANCE-14-CAMERAS.md`.

### Fuel sources + optional local counter alert bridge (Nov 2026)

Includes a **Fuel Sources** web tab, `FuelSources.gs`, separate AAA / GasBuddy / MostEdge source tasks, evidence-linked reference prices, store fuel-report entry, reconciliation and an owner-installed daily task generator. See `docs/FUEL-SOURCES.md`. Public or protected sites are **not automatically scraped**; real data is entered by approved users or a separately licensed feed. A separate optional `edge-agent/` service accepts occupancy events from an already configured camera-analytics system and can send a neutral staff-assistance announcement through a configured Home Assistant speaker. **It does not include live computer vision or camera connectivity by itself.**

## Start here

1. Open **`preview/OM-AI-preview.html`** in your browser. This is a **fully labeled fictional demo**; it is not connected to any service and cannot save records.
2. Follow **`docs/SETUP.md`** to deploy the private Google Apps Script app, create a fresh private Google Sheets database, configure permissions, and activate integrations.
3. Read **`docs/SECURITY.md`** before inviting your staff or linking from the existing public GitHub Pages site.
4. To import historical store performance, use **`docs/DATA-DICTIONARY.md`** and `samples/normalized-sales.csv` as the required normalized schema. Messy existing sheets need a mapping/cleanup step.

### What is implemented

| Area | Live functionality after deployment | Conditions / limitations |
| --- | --- | --- |
| Overview | Store-specific KPIs, sales trends, computed alerts | Requires real entered/imported data |
| OM Impact | Explains which internal/external signals deserve attention and why; source relevance, not causal proof | Automated classification and human review |
| OM Radar | NWS forecast/alerts, optional TomTom nearby road speeds/incident feed, news RSS mentions, manual verified roadwork events | Coordinates required; TomTom needs key; 511 is linked, not scraped |
| OM Insights | Daily sales, customers, fuel gallons, lottery, vendor invoice-to-audit reconciliation | Data entered/imported from store source |
| OM Predict | Explainable 7-day same-weekday sales baseline and heuristic ranges | >=14 records to start; >=3 comparable weekdays per prediction |
| OM Alerts | Low stock, overdue tasks, vendor differences, open high incidents, recorded roadwork and NWS weather alerts | Rule-driven; no unsupported assertions of causality |
| OM Watch | Incident logging and incident summary | No raw CCTV in Google Sheets |
| OM Cameras | 14-camera proposed coverage, observer tasks, camera event aggregates, road/pump/store/wash analytics, explicit heartbeats | Optional local Frigate NVR and POS/controller data must be configured; no live streams in Sheet |
| OM Control | Tasks, statuses, reorder monitoring | Manual entries, not automatic POS inventory |
| OM Advisor | Optional Gemini response grounded on aggregate store context | API key/quotas/model required; no secrets sent |
| OM Finance | Operating expense entries, ATM/lottery/fuel/car wash metrics | No direct bank/ATM provider connection |
| Compliance | Permit/deadline tracker, overdue reminders | Dates must be confirmed by you |
| Multi-store | Store selector, Admin/Manager/Viewer UI access checks | Google Sheet sharing must be considered separately; it is not true per-store isolation |
| Auto-refresh | Owner-installed hourly source poll; optional owner-configured digest function | Apps Script triggers and provider quotas apply |

### Architecture

```text
Staff Google account (permission checked)
         |
Private Apps Script HTML Service dashboard
         | google.script.run (same-origin, no browser CORS hacks)
         v
Apps Script backend -- SpreadsheetApp -> separate private OM AI Google Sheet
         |
         +-- NWS public weather API (US stores)
         +-- TomTom Traffic API (optional private API key)
         +-- Google News RSS headlines (best effort; unverified)
         +-- Gemini generateContent (optional private API key)

GitHub: version-controlled source only. Existing public GitHub Pages
should contain a LINK to this private app, not private API responses.
```

### File list

- `apps-script/Config.gs` — schema, security checks, Sheet I/O, sanitization
- `apps-script/Setup.gs` — creates private Sheets, seed store names, hourly trigger
- `apps-script/Api.gs` — private web app, dashboard reads, entries, updates, historical importer
- `apps-script/Analysis.gs` — KPI formulas, rule alerts, baseline forecasts
- `apps-script/Monitor.gs` — NWS, TomTom, Google News adapters, scheduled refresh
- `apps-script/FuelSources.gs` — audited reference prices, MostEdge reports, daily source tasks
- `apps-script/CameraSync.gs` — 14-camera planning, signed aggregate ingestion and observer checklist
- `surveillance/` — local edge collector, Frigate MQTT adapter, secure hourly sync and example configurations
- `apps-script/AI.gs` — optional Gemini assistant with limited aggregate context
- `apps-script/Index.html` — private app shell
- `apps-script/Styles.html` — responsive dashboard styles
- `apps-script/Client.html` — dashboard rendering and interactions
- `apps-script/appsscript.json` — Apps Script manifest/scopes
- `preview/OM-AI-preview.html` — local, illustrative read-only preview
- `docs/` — step-by-step setup, data dictionary, security notes
- `tests/` — local Node/browser smoke tests

### Relationship to existing repository

Your existing source repo `OMUniversalLLC/om-universal-operations-dashboard` already has a separate public GitHub Pages reporting mode and a Google login gateway. **Do not overwrite its existing `google-apps-script/Code.gs`** with OM AI: both apps define a `doGet()` and use different permission/data models. Deploy OM AI as **a separate Apps Script project**, then add a link to the private OM AI `/exec` URL from your existing dashboard menu after confirming access controls.

The existing repository has not been changed by this ZIP. No deployment, Google Sheet connection, API subscription, or GitHub push has been performed.

### Limits and production checklist

**Security boundary:** Apps Script checks stores by role, but sharing one underlying Google Sheet lets recipients see its entire file, even if the UI filters to one store. Use only trusted staff with appropriate whole-file access. Strict per-store isolation requires separate data files or a different server-side identity architecture. Owner-only protections are set for Users, Stores, and AuditLog.\n\nThis is a functional MVP rather than an enterprise-ready, fully-integrated system. It does not automatically read existing POS, MercuryOne, bank, CCTV, ATM, local FDOT roadwork databases or live car wash devices. Confirm user access; add source mappings, backups, data retention, error monitoring and per-provider API terms before broad staff use. Financial forecasts are explanatory baselines, not guaranteed outcomes. Some third-party API endpoints, pricing and quotas may change.

## Validation

Run `node tests/test.mjs` (requires Node 18+). The browser demo is static and runs offline using fabricated records. After Apps Script deployment, test a Viewer, Manager and Admin with real Google permissions before relying on it operationally.

### New: OM WiFi Intelligence (network and camera health)

The **OM WiFi** tab adds mobile/desktop monitoring of NVR reachability, configured LAN devices, PC Wi-Fi quality, router-provided connected-client lists (optional), and 14 optional camera-stream checks. Its Windows-only basic agent uses Python stdlib and sends **signed status metadata only** to private Sheets when enabled. It does **not** auto-scan networks, prove every connected Wi-Fi client from ARP, assume PoE cameras are Wi-Fi, or claim NVR recording solely from RTSP. All channel probes are initially disabled and the UI remains unconfigured until the store setup is complete.

Start with `network-agent/README.md` and `docs/WIFI-INTELLIGENCE.md`. New private Sheet tabs: `NetworkStatus`, `NetworkDevices`, `NetworkCameras`, `NetworkEvents`. Call `setupOmAi()` as the owner to add them; original 14-camera setup is unchanged. Separate HMAC secret `OM_WIFI_SYNC_SECRET` required. No GitHub push or live deployment performed.
