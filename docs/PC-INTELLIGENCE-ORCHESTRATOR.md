# OM AI — PC Intelligence & Task Orchestrator

**Release:** 2026-11-19 development package. **State:** Code and local demo, not connected to a physical store computer or public website.

## What is built

- `pc-agent/agent.py`: Windows-oriented read-only CPU, RAM, PC storage and process metrics (psutil); optional temperature/GPU sensor receipt; risk rules; signed local-to-private Apps Script status upload; historical summary retention.
- `pc-agent/desktop_app.py` + `launch-pc-app.bat`: local **OM PC Companion** window for operator review. No process stopping, remote terminal, forced reboot or account control.
- `apps-script/PcTaskMonitor.gs`: private HMAC-verified telemetry ingestion and stale-status handling; review audit trail.
- `apps-script/ServiceJobs.gs`: actual Apps Script NWS/TomTom/Google News refresh outcomes produce dated server-side job receipts (not claims of data correctness).
- `apps-script/AiOps.gs`: manager-initiated, optional Gemini or OpenAI API task analysis on **sanitized job metadata only**. No AI task execution or system mutation.
- `Client.html`: **OM PC** and **OM Orchestrator** pages, responsive to mobile and desktop.

## Data that stays separate

| System | Data | How linked | What is NOT implied |
|---|---|---|---|
| iLink NVR | Recording and native AI events | Previous OM Cameras module | RTSP responding does not prove recorded footage |
| Store Windows PC | CPU/RAM/disk/processes | psutil agent | CPU load does not equal temperature |
| Local sensor source | CPU/GPU temperature and GPU% | Validated local `sensors.json` | No source = **Not measured**, not safe temperature |
| Network / Wi-Fi | Router exports, TCP probes, RTSP checks | Previous OM WiFi module | ARP does not mean connected to Wi-Fi |
| Apps Script scheduled refresh | NWS/traffic/news outcomes | `ServiceJobs` actual completion records | A successful fetch does not prove an incident or a profit impact |
| GasBuddy/AAA/MostEdge | Fuel reference values and reports | Evidence-based daily task receipts | No paid/API access or direct scraping is included |
| AI provider | Task interpretation | Optional selected API; manager-only | This is not your ChatGPT account, and no action is authorized |

## Intelligent rules already implemented

1. Missing monitor heartbeat or old telemetry is marked stale.
2. Sustained high RAM pressure is distinguished from a single reading.
3. High CPU use flags optional analytics for review, not NVR recording changes.
4. Missing CPU temperature is flagged as **unmeasured**.
5. Actual high temperature, when reliably measured, triggers a ventilation/inference review.
6. Low disk free space triggers log retention/backup review, never automatic file deletion.
7. Protected service process not seen prompts verification, not forced restart.
8. Missing task receipts stay **not connected**.
9. Task failures, skipped runs and overdue reports remain separate states.
10. Tasks requiring evidence cannot be healthy without a dated, HTTPS source reference.
11. Manager job review is audited without changing the job's underlying execution state.
12. Multi-signal hypotheses (camera analytics delays + RAM pressure, multiple job failures) are clearly **correlation, not proof**.
13. External refresh jobs record observed API success/partial/failure instead of being marked complete just because a trigger exists.
14. Optional Gemini/OpenAI analysis is manager-requested; it cannot kill processes, change fuel prices, adjust payroll, or close tasks automatically.

## Installation steps (without editing your existing live website)

**Step 1 — Private database**

Create or use a **separate Apps Script project** for the private OM AI application. Copy all files in `apps-script/` into their matching `.gs` and `.html` files. Redeploy the private web app and **run `setupOmAi()` again** as owner so these new tabs exist: `PcStatus`, `PcJobs`, `PcAlerts`, `JobReviews`, `ServiceJobs`. Keep the existing public GitHub Pages report separate from confidential monitoring data. Validate access with an Admin, Manager and Viewer.

**Step 2 — Windows companion**

Copy the `pc-agent/` directory to the approved store PC. Install Python and `psutil`, then `py desktop_app.py` for the local GUI. Configure `config.local.json` and run `py agent.py --config config.local.json --dry-run` before enabling an actual 5-minute Task Scheduler job. Set Scheduled Task option **Do not start a new instance** to avoid overlap.

**Step 3 — Optional protected synchronization**

Generate a random shared `OM_PC_SYNC_SECRET` (minimum 32 characters). Store it in *private* Apps Script Properties and in the store PC's protected user/service environment. Set `OM_PC_SYNC_URL` to the **private Apps Script** `/exec` deployment URL. A signed status packet can then update the Sheets. The website automatically shows data as stale if no PC update arrives for 15 minutes. Without this setup, data stays on the PC.

**Step 4 — Real automation receipts**

A scheduled system should emit a structured `job-receipts.json` *after* the authorized action finishes, with a real dated result. Do not create `success` entries just because something was scheduled. Existing Apps Script weather/traffic/news refreshes write their own service receipts after actual calls. GasBuddy and MostEdge still require approved access, a licensed feed or human-verifiable export; no assumed public API is used. The local agent does not call those sites itself.

**Step 5 — AI providers (optional)**

- To use the existing Gemini implementation: set `GEMINI_API_KEY` and supported `GEMINI_MODEL` in Apps Script Properties.
- For OpenAI task review: set `OPENAI_API_KEY` and an actual supported `OPENAI_MODEL` in Script Properties. OpenAI API use is separate from ChatGPT's app subscription and any ChatGPT Automations.
- AI review sends limited data about the specific job, not raw customer footage, employee activity logs, or process command lines.
- Review output is advisory. A human must validate against the primary source.

## Safety and operations

- The PC process monitor has **no endpoint or function** to End Task or alter operating system settings.
- Never stop surveillance, NVR, AV/security, POS, payment, backup, or unknown processes to “cool” the PC.
- Start with observational thresholds and review several days of normal operating measurements before tuning.
- For AMD temperature/GPU sensors, use a tested local sensor export. Windows `psutil` alone usually cannot measure them. Some LibreHardwareMonitor releases have WMI bugs; confirm compatibility before relying on the readings.
- Keep remote desktop, RTSP, NVR ports, credentials, source code secrets and raw clips off public GitHub Pages. Use a private login/VPN and least privilege.
- Any future task execution or configuration change should require authentication, explicit approvals, logging and rollback design.

## Next possible AI modules (not implemented by this release)

**OM Guardian:** correlate network outages + camera feed failures; **OM Smart Cooling:** optional AI inference throttling with an authorized control contract; **OM Vision QA:** validation against manual people and vehicle counts; **OM Profit Brain:** quantify margins and actual transaction effects; **OM Data Auditor:** prevent wrong invoices, missing fuel grades and stale prices; **OM Supply Watch:** vendor delay prediction; **OM Compliance Sentinel:** verified permit and inspection reminders. These are planned expansions, not live operational features.

## Tests

- `python -m unittest discover -s pc-agent/tests -v`
- `python -m unittest discover -s network-agent/tests -v`
- `python -m unittest discover -s surveillance/tests -v`
- `node tests/test.mjs`
- `python tests/browser_pc_orchestrator.py` (requires Playwright and a local Chromium executable; adapt its path as needed)

This code has **not** been installed on the store PC, signed in to Google, connected to cameras or deployed to your production site. A tested local browser demonstration is not proof of production infrastructure working.
